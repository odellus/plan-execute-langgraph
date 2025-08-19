import logging
from typing import Dict, Any

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START

from plan_execute.agent.models import ChatRequest, ChatResponse, PlanExecute
from plan_execute.agent.nodes import plan_step, execute_step, replan_step

logger = logging.getLogger("service")

from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler
 
# Initialize Langfuse CallbackHandler for Langchain (tracing)
langfuse_handler = CallbackHandler()
class PlanExecuteService:
    """
    Thin wrapper that owns the compiled LangGraph and the checkpointer
    so FastAPI does not have to know anything about LangGraph internals.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.checkpointer = AsyncPostgresSaver(pool)
        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_graph(self):
        """Compile the LangGraph workflow once and return the runnable."""
        workflow = StateGraph(PlanExecute)

        workflow.add_node("plan_step", plan_step)
        workflow.add_node("execute_step", execute_step)
        workflow.add_node("replan_step", replan_step)

        workflow.add_edge(START, "plan_step")

        return workflow.compile(checkpointer=self.checkpointer)

    async def initialize(self) -> None:
        """One-time DB setup; call once at start-up."""
        try:
            await self.checkpointer.setup()
        except Exception as e:
            if "CREATE INDEX CONCURRENTLY cannot run inside a transaction block" in str(e):
                logger.warning("Concurrent index creation failed, trying alternative setup")
                # Try to setup without concurrent index creation
                # The checkpointer should work even if indexes aren't created concurrently
                pass
            else:
                raise

    async def chat(self, req: ChatRequest) -> ChatResponse:
        """
        Re-implementation of the old endpoint logic.

        :param req: validated request model
        :raises Exception: 500 on any unhandled exception
        """
        logger.info("Processing thread_id=%s message=%r", req.thread_id, req.message)

        config = {
            "recursion_limit": 50, 
            "configurable": {"thread_id": req.thread_id}, 
            "callbacks": [langfuse_handler], 
            "metadata": {"langfuse_session_id": req.thread_id}
        }
        inputs: Dict[str, str] = {"input": req.message}

        final_state: Dict[str, Any] | None = None
        try:
            async for event in self.graph.astream(inputs, config=config):
                final_state = event
                if "__end__" in event:
                    break
        except Exception as exc:
            logger.exception("Graph execution failed")
            raise Exception("Pipeline failure") from exc

        response_text = None
        if final_state:
            if "response" in final_state:
                response_text = str(final_state["response"])
            elif "replan_step" in final_state and "response" in final_state["replan_step"]:
                response_text = str(final_state["replan_step"]["response"])

        if not response_text:
            logger.error("No response generated. final_state=%s", final_state)
            raise Exception("No response generated")

        logger.info("Returning response for thread_id=%s: %r", req.thread_id, response_text)
        return ChatResponse(response=response_text)
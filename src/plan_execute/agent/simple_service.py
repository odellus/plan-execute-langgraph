import logging
from typing import Dict, Any, AsyncGenerator
from typing_extensions import TypedDict

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from plan_execute.agent.models import ChatRequest
from plan_execute.config import settings

from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("simple_service")
langfuse_handler = CallbackHandler()

class SimpleChatState(TypedDict):
    messages: list
    response: str


class SimpleChatResponse(BaseModel):
    response: str


class SimpleAgentService:
    """
    A simple agent service that streams responses back to the client.
    This is a much simpler alternative to the complex plan-execute agent.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.checkpointer = AsyncPostgresSaver(pool)
        self.graph = self._build_graph()
        self.llm = ChatOpenAI(
            model="claude4_sonnet",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
            streaming=True,
        )

    def _build_graph(self):
        """Build a simple graph that just processes messages and responds."""
        workflow = StateGraph(SimpleChatState)
        
        # Add a single node that processes the message and generates a response
        workflow.add_node("respond", self._respond_node)
        
        # Connect START to the respond node
        workflow.add_edge(START, "respond")
        
        # Connect respond node to END
        workflow.add_edge("respond", END)
        
        return workflow.compile(checkpointer=self.checkpointer)

    async def _respond_node(self, state: SimpleChatState) -> Dict[str, Any]:
        """Simple node that generates a response to the user's message."""
        try:
            # Get the last message
            last_message = state["messages"][-1] if state["messages"] else None
            
            if not last_message:
                return {"response": "I didn't receive any message."}
            
            # Create a simple prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Respond directly and helpfully to the user's message."),
                ("user", "{input}")
            ])
            
            # Generate response - collect all chunks into complete response
            chain = prompt | self.llm
            full_response = ""
            async for chunk in chain.astream({"input": last_message.content}, config=dict(callbacks=[langfuse_handler])):
                if chunk.content:
                    full_response += chunk.content
            
            return {"response": full_response}
            
        except Exception as e:
            logger.error(f"Error in respond node: {e}")
            return {"response": f"I'm sorry, I encountered an error: {str(e)}"}

    async def initialize(self) -> None:
        """One-time DB setup; call once at start-up."""
        await self.checkpointer.setup()

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream chat responses back to the client.
        
        :param req: validated request model
        :yields: chunks of the response as they're generated
        """
        logger.info("Processing streaming chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        try:
            # Create a simple prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Respond directly and helpfully to the user's message."),
                ("user", "{input}")
            ])
            
            # Stream directly from the LLM, bypassing LangGraph for streaming
            chain = prompt | self.llm
            
            async for chunk in chain.astream({"input": req.message}, config=dict(callbacks=[langfuse_handler])):
                if chunk.content:
                    # Yield each chunk as it arrives
                    yield f"data: {chunk.content}\n\n"
            
            # Signal completion
            yield "data: [DONE]\n\n"
                    
        except Exception as exc:
            logger.exception("Streaming chat execution failed")
            yield f"data: Error: {str(exc)}\n\n"
            yield "data: [DONE]\n\n"

    async def chat(self, req: ChatRequest) -> SimpleChatResponse:
        """
        Non-streaming chat method for compatibility.
        
        :param req: validated request model
        :returns: complete response
        """
        logger.info("Processing chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        config = {"recursion_limit": 10, "configurable": {"thread_id": req.thread_id}}
        inputs: Dict[str, Any] = {
            "messages": [HumanMessage(content=req.message)],
            "response": ""
        }
        
        try:
            # Run the graph and get the final result
            result = await self.graph.ainvoke(inputs, config=config)
            response_text = result.get("response", "No response generated")
            
            return SimpleChatResponse(response=response_text)
            
        except Exception as exc:
            logger.exception("Graph execution failed")
            raise Exception("Chat execution failed") from exc


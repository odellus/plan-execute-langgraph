import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent import get_graph  # <-- import the compiled graph builder
from config import settings
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app")

# ------------------------------------------------------------------
# Lifespan: create one shared pool and checkpointer
# ------------------------------------------------------------------
db_uri = settings.postgres_dsn
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncConnectionPool(db_uri, open=False) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        app.state.checkpointer = checkpointer  # store for handlers
        yield
    # pool closed automatically on exit

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"

class ChatResponse(BaseModel):
    response: str

# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    logger.info("Incoming chat request: thread_id=%s message=%r", req.thread_id, req.message)
    checkpointer = app.state.checkpointer
    graph = get_graph(checkpointer)

    config = {"recursion_limit": 50, "configurable": {"thread_id": req.thread_id}}
    inputs = {"input": req.message}

    final_state = None
    try:
        async for event in graph.astream(inputs, config=config):
            final_state = event
            if "__end__" in event:
                break
    except Exception as exc:
        logger.exception("LangGraph pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc))

    # NEW: dig one level deeper when the last node is 'replan_step'
    response_text = None
    if final_state:
        if "response" in final_state:                       # top-level key
            response_text = final_state["response"]
        elif "replan_step" in final_state and "response" in final_state["replan_step"]:
            response_text = final_state["replan_step"]["response"]

    if not response_text:
        logger.error("No response generated. final_state=%s", final_state)
        raise HTTPException(status_code=500, detail="No response generated")

    logger.info("Returning response: %r", response_text)
    return ChatResponse(response=response_text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
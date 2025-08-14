import traceback
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from plan_execute.config import settings
from plan_execute.agent.models import ChatRequest, ChatResponse
from plan_execute.agent.service import PlanExecuteService
from plan_execute.agent.simple_service import SimpleAgentService

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
        # Initialize both services
        plan_execute_service = PlanExecuteService(pool)
        simple_agent_service = SimpleAgentService(pool)
        
        await plan_execute_service.initialize()
        await simple_agent_service.initialize()
        
        app.state.plan_execute_executor = plan_execute_service
        app.state.simple_agent_executor = simple_agent_service
        
        yield
    # pool closed automatically on exit

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now to debug
    allow_credentials=False,  # Set to False when using allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Original Plan-Execute Endpoint
# ------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    service: PlanExecuteService = app.state.plan_execute_executor
    try:
        return await service.chat(ChatRequest(**req.model_dump()))
    except Exception as exc:
        detail = traceback.format_exc()
        logger.exception("chat endpoint failed")
        raise HTTPException(status_code=500, detail=detail)


# ------------------------------------------------------------------
# Simple Agent Streaming Endpoint
# ------------------------------------------------------------------
from fastapi.responses import StreamingResponse

@app.options("/simple-chat-stream")
async def simple_chat_stream_options():
    """Handle CORS preflight for simple-chat-stream"""
    logger.info("OPTIONS request received for /simple-chat-stream")
    return {"message": "OK"}

@app.post("/simple-chat-stream")
async def simple_chat_stream(req: ChatRequest):
    """
    Streaming endpoint for the simple agent.
    Returns Server-Sent Events (SSE) format.
    """
    service: SimpleAgentService = app.state.simple_agent_executor
    try:
        return StreamingResponse(
            service.chat_stream(req),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except Exception as exc:
        detail = traceback.format_exc()
        logger.exception("simple chat stream endpoint failed")
        raise HTTPException(status_code=500, detail=detail)


# ------------------------------------------------------------------
# Simple Agent Non-Streaming Endpoint (for compatibility)
# ------------------------------------------------------------------
@app.post("/simple-chat", response_model=ChatResponse)
async def simple_chat(req: ChatRequest) -> ChatResponse:
    """
    Non-streaming endpoint for the simple agent.
    """
    service: SimpleAgentService = app.state.simple_agent_executor
    try:
        result = await service.chat(req)
        return ChatResponse(response=result.response)
    except Exception as exc:
        detail = traceback.format_exc()
        logger.exception("simple chat endpoint failed")
        raise HTTPException(status_code=500, detail=detail)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("plan_execute.app:app", host=settings.host, port=settings.port)
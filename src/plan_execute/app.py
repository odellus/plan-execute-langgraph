import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from plan_execute.config import settings
from plan_execute.agent.models import ChatRequest, ChatResponse
from plan_execute.agent.service import PlanExecuteService

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
        service = PlanExecuteService(pool)   # << new service
        await service.initialise()
        app.state.executor = service       # << attach to app state
        yield
    # pool closed automatically on exit

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------
app = FastAPI(lifespan=lifespan)


# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    service: PlanExecuteService = app.state.executor
    try:
        return await service.chat(ChatRequest(**req.model_dump()))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("plan_execute.app:app", host=settings.host, port=settings.port)
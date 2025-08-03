from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from dotenv import load_dotenv
import os
import asyncpg

load_dotenv()

class PlanExecuteService:
    def __init__(self, db_uri: str):
        self.db_uri = db_uri
        self._pool: asyncpg.Pool | None = None
        self._checkpointer: AsyncPostgresSaver | None = None

    async def __aenter__(self):
        self._pool = await asyncpg.create_pool(self.db_uri, min_size=1, max_size=10)
        self._checkpointer = AsyncPostgresSaver(self._pool)
        await self._checkpointer.setup()          # create tables if they don’t exist
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._pool:
            await self._pool.close()

    @property
    def checkpointer(self) -> AsyncPostgresSaver:
        if self._checkpointer is None:
            raise RuntimeError("Service not started. Use async context manager.")
        return self._checkpointer
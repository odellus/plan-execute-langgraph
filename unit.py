#!/usr/bin/env python3
"""
Unit-level test that runs the **exact same graph** the service uses,
but with the real Postgres checkpointer (no FastAPI, no HTTP).
"""

import asyncio
from config import settings
from agent import get_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def main():
    async with AsyncPostgresSaver.from_conn_string(settings.postgres_dsn) as checkpointer:
        await checkpointer.setup()
        app = get_graph(checkpointer)

        config = {"recursion_limit": 50, "configurable": {"thread_id": "unit_test"}}
        inputs = {"input": "How do I take over the world?"}

        async for event in app.astream(inputs, config=config):
            for k, v in event.items():
                if k != "__end__":
                    print(v)


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Quick smoke-test for the /chat endpoint.
"""

import asyncio
import httpx
from plan_execute.config import settings

async def chat(message: str, thread_id: str = "test") -> str:
    url = f"http://{settings.host}:{settings.port}/chat"
    payload = {"message": message, "thread_id": thread_id}
    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["response"]


async def main():
    try:
        answer = await chat("Look on wikipedia for the hometown of the winner of the 1997 NBA MVP Award?", thread_id="12346")
        print("🤖", answer)
    except Exception as e:
        print("❌", e)


if __name__ == "__main__":
    asyncio.run(main())
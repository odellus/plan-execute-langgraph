#!/usr/bin/env python3
"""
Quick smoke-test for the /chat endpoint.
"""

import asyncio
import httpx
from plan_execute.config import settings

async def chat(message: str, thread_id: str = "test") -> str:
    url = f"http://localhost:{settings.port}/chat"
    payload = {"message": message, "thread_id": thread_id}
    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["response"]


async def main():
    try:
        answer = await chat(
            "Refine using lots of search a means for taking over the world by smashing IP and building a soviet of technicians to circumvent ruinous artificial scarcity", 
            thread_id="123417",
        )
        print("🤖", answer)
    except Exception as e:
        print("❌", e)


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Quick smoke-test for the /chat endpoint.
"""

import asyncio
import httpx


async def chat(message: str, thread_id: str = "test") -> str:
    url = "http://localhost:8000/chat"
    payload = {"message": message, "thread_id": thread_id}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["response"]


async def main():
    try:
        answer = await chat("How do I take over the world? Be specific and concise. Stop early")
        print("🤖", answer)
    except Exception as e:
        print("❌", e)


if __name__ == "__main__":
    asyncio.run(main())
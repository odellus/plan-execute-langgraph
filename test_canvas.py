#!/usr/bin/env python3
"""
Test script for canvas functionality
"""

import asyncio
import logging
from psycopg_pool import AsyncConnectionPool
from src.plan_execute.canvas.service import CanvasService
from src.plan_execute.canvas.models import CanvasChatRequest
from src.plan_execute.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_canvas_service():
    """Test the canvas service functionality."""
    
    # Create a connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False) as pool:
        # Initialize canvas service
        canvas_service = CanvasService(pool)
        await canvas_service.initialize()
        
        # Test 1: Create a Python function
        print("=== Test 1: Create a Python function ===")
        request1 = CanvasChatRequest(
            message="Create a Python function that calculates the factorial of a number"
        )
        
        response1 = await canvas_service.chat(request1)
        print(f"Response: {response1.message}")
        if response1.artifact:
            content = response1.artifact.contents[0]
            print(f"Artifact type: {content.type}")
            print(f"Artifact title: {content.title}")
            if content.type == "code":
                print(f"Language: {content.language}")
                print(f"Code:\n{content.code}")
        
        # Test 2: Modify the existing code
        print("\n=== Test 2: Modify the existing code ===")
        request2 = CanvasChatRequest(
            message="Add error handling and docstring to the function",
            artifact=response1.artifact
        )
        
        response2 = await canvas_service.chat(request2)
        print(f"Response: {response2.message}")
        if response2.artifact:
            content = response2.artifact.contents[0]
            print(f"Modified code:\n{content.code}")
        
        # Test 3: Create a markdown document
        print("\n=== Test 3: Create a markdown document ===")
        request3 = CanvasChatRequest(
            message="Create a README file for a Python project about machine learning"
        )
        
        response3 = await canvas_service.chat(request3)
        print(f"Response: {response3.message}")
        if response3.artifact:
            content = response3.artifact.contents[0]
            print(f"Artifact type: {content.type}")
            print(f"Markdown content:\n{content.fullMarkdown}")

if __name__ == "__main__":
    asyncio.run(test_canvas_service())
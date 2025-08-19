#!/usr/bin/env python3
"""
Test script for DSPy MCP integration.
Tests both the MCP server and the integrated DSPy service.
"""
import asyncio
import json
import logging
import subprocess
import time
from typing import AsyncGenerator

import aiohttp
from psycopg_pool import AsyncConnectionPool

from src.plan_execute.agent.dspy_mcp_service import DSPyMCPAgentService
from src.plan_execute.agent.models import ChatRequest
from src.plan_execute.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mcp_test")


async def test_mcp_server_standalone():
    """Test that the MCP server can be started and responds to tool requests."""
    logger.info("Testing MCP server standalone functionality...")
    
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import dspy
        
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=["/Users/thomas.wood/src/plan-execute-langgraph/mcp_server.py"],
            env=None,
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                logger.info(f"Found {len(tools.tools)} MCP tools:")
                for tool in tools.tools:
                    logger.info(f"  - {tool.name}: {tool.description}")
                
                # Convert to DSPy tools and test one
                dspy_tools = []
                for tool in tools.tools:
                    dspy_tool = dspy.Tool.from_mcp_tool(session, tool)
                    dspy_tools.append(dspy_tool)
                
                # Test fetch_flight_info tool
                fetch_flight_tool = next((t for t in dspy_tools if t.name == "fetch_flight_info"), None)
                if fetch_flight_tool:
                    logger.info("Testing fetch_flight_info tool...")
                    result = await fetch_flight_tool.acall(
                        date={"year": 2025, "month": 9, "day": 1, "hour": 0},
                        origin="SFO",
                        destination="JFK"
                    )
                    logger.info(f"Flight search result: {result}")
                
                logger.info("✓ MCP server standalone test passed")
                return True
                
    except Exception as e:
        logger.error(f"✗ MCP server standalone test failed: {e}")
        return False


async def test_dspy_mcp_service():
    """Test the DSPy MCP service integration."""
    logger.info("Testing DSPy MCP service integration...")
    
    try:
        # Create connection pool
        db_uri = settings.postgres_dsn
        async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
            # Initialize service
            service = DSPyMCPAgentService(pool)
            await service.initialize()
            
            # Test chat request
            request = ChatRequest(
                thread_id="test-mcp-thread",
                message="Please help me find flights from SFO to JFK on September 1st, 2025"
            )
            
            logger.info("Testing non-streaming chat...")
            response = await service.chat(request)
            logger.info(f"Non-streaming response: {response.response}")
            
            # Test streaming chat
            logger.info("Testing streaming chat...")
            stream_chunks = []
            async for chunk in service.chat_stream(request):
                if chunk.strip() and not chunk.startswith("data: [DONE]"):
                    stream_chunks.append(chunk)
                    # Parse the streaming chunk to see the content
                    if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                        try:
                            chunk_data = json.loads(chunk[6:])  # Remove "data: " prefix
                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    logger.info(f"Streaming content: {delta['content']}")
                        except json.JSONDecodeError:
                            pass
            
            logger.info(f"✓ DSPy MCP service test passed - received {len(stream_chunks)} chunks")
            return True
            
    except Exception as e:
        logger.error(f"✗ DSPy MCP service test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_api_endpoints():
    """Test the API endpoints with the MCP service."""
    logger.info("Testing API endpoints...")
    
    # Start the server in the background
    server_process = None
    try:
        logger.info("Starting FastAPI server...")
        server_process = subprocess.Popen(
            ["python", "-m", "src.plan_execute.app"],
            cwd="/Users/thomas.wood/src/plan-execute-langgraph"
        )
        
        # Wait for server to start
        await asyncio.sleep(5)
        
        # Test the airline chat endpoint
        async with aiohttp.ClientSession() as session:
            url = f"http://{settings.host}:{settings.port}/airline-chat"
            payload = {
                "thread_id": "test-api-thread",
                "message": "I need to book a flight from SFO to JFK on September 1st, 2025. My name is Adam."
            }
            
            logger.info(f"Testing POST {url}")
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"API response: {result}")
                    logger.info("✓ API endpoint test passed")
                    return True
                else:
                    logger.error(f"✗ API endpoint test failed with status {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    return False
                    
    except Exception as e:
        logger.error(f"✗ API endpoint test failed: {e}")
        return False
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait()


async def test_streaming_endpoint():
    """Test the streaming API endpoint."""
    logger.info("Testing streaming API endpoint...")
    
    # Start the server in the background
    server_process = None
    try:
        logger.info("Starting FastAPI server for streaming test...")
        server_process = subprocess.Popen(
            ["python", "-m", "src.plan_execute.app"],
            cwd="/Users/thomas.wood/src/plan-execute-langgraph"
        )
        
        # Wait for server to start
        await asyncio.sleep(5)
        
        # Test the airline streaming chat endpoint
        async with aiohttp.ClientSession() as session:
            url = f"http://{settings.host}:{settings.port}/airline-chat-stream"
            payload = {
                "thread_id": "test-stream-thread",
                "message": "Please help me book a flight from SFO to JFK on September 1st, 2025. My name is Bob."
            }
            
            logger.info(f"Testing streaming POST {url}")
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    chunks_received = 0
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line and not line == "data: [DONE]":
                            chunks_received += 1
                            if line.startswith("data: "):
                                try:
                                    chunk_data = json.loads(line[6:])
                                    if "choices" in chunk_data and chunk_data["choices"]:
                                        delta = chunk_data["choices"][0].get("delta", {})
                                        if "content" in delta and delta["content"]:
                                            logger.info(f"Streamed: {delta['content']}")
                                except json.JSONDecodeError:
                                    pass
                        elif line == "data: [DONE]":
                            break
                    
                    logger.info(f"✓ Streaming API test passed - received {chunks_received} chunks")
                    return True
                else:
                    logger.error(f"✗ Streaming API test failed with status {response.status}")
                    text = await response.text()
                    logger.error(f"Response: {text}")
                    return False
                    
    except Exception as e:
        logger.error(f"✗ Streaming API test failed: {e}")
        return False
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait()


async def main():
    """Run all tests."""
    logger.info("Starting DSPy MCP integration tests...")
    
    tests = [
        ("MCP Server Standalone", test_mcp_server_standalone),
        ("DSPy MCP Service", test_dspy_mcp_service),
        ("API Endpoints", test_api_endpoints),
        ("Streaming Endpoint", test_streaming_endpoint),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            results[test_name] = await test_func()
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! MCP integration is working correctly.")
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script for simple-chat endpoint with MCP integration.
Tests the enhanced DSPy service through the existing simple-chat endpoints.
"""
import asyncio
import logging
from psycopg_pool import AsyncConnectionPool

from src.plan_execute.agent.dspy_service import DSPyAgentService
from src.plan_execute.agent.models import ChatRequest
from src.plan_execute.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("simple_chat_mcp_test")


async def test_simple_chat_with_mcp():
    """Test the enhanced simple-chat service with MCP tools."""
    logger.info("🧪 Testing Simple Chat with MCP Integration")
    
    # Create connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        # Initialize the enhanced DSPy service
        service = DSPyAgentService(pool)
        await service.initialize()
        
        if service.mcp_tools:
            logger.info(f"✓ Service initialized with {len(service.mcp_tools)} MCP tools")
        else:
            logger.info("✓ Service initialized without MCP tools (fallback mode)")
        
        # Test scenarios
        test_cases = [
            {
                "name": "General Conversation",
                "message": "Hello! How are you today?",
                "thread_id": "test-general"
            },
            {
                "name": "Flight Search",
                "message": "Can you help me find flights from SFO to Boston on December 19th, 2024?",
                "thread_id": "test-flight-search"
            },
            {
                "name": "Flight Booking",
                "message": "Please book the cheapest flight from SFO to Boston on December 19th, 2024 for Adam.",
                "thread_id": "test-booking"
            },
            {
                "name": "Mixed Conversation",
                "message": "Hi! I'm planning a trip. Can you tell me what flights are available from LAX to JFK on September 1st, 2025?",
                "thread_id": "test-mixed"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Test Case {i}: {test_case['name']}")
            logger.info(f"{'='*60}")
            logger.info(f"User: {test_case['message']}")
            logger.info(f"{'-'*60}")
            
            # Create request
            request = ChatRequest(
                thread_id=test_case['thread_id'],
                message=test_case['message']
            )
            
            try:
                # Test non-streaming
                logger.info("Testing non-streaming response...")
                response = await service.chat(request)
                logger.info(f"Assistant: {response.response}")
                
                # Test streaming
                logger.info("\nTesting streaming response...")
                stream_content = ""
                async for chunk in service.chat_stream(request):
                    if chunk.strip() and not chunk.startswith("data: [DONE]"):
                        # Parse streaming chunks to extract content
                        if chunk.startswith("data: "):
                            try:
                                import json
                                chunk_data = json.loads(chunk[6:])  # Remove "data: " prefix
                                if "choices" in chunk_data and chunk_data["choices"]:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    if "content" in delta and delta["content"]:
                                        content = delta["content"]
                                        print(content, end="", flush=True)
                                        stream_content += content
                            except json.JSONDecodeError:
                                pass
                
                print()  # New line after streaming
                logger.info("✓ Test case completed successfully")
                
            except Exception as e:
                logger.error(f"❌ Test case failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Small delay between test cases
            await asyncio.sleep(1)
        
        logger.info(f"\n{'='*60}")
        logger.info("🎉 Simple Chat MCP Integration Test Completed!")
        logger.info("The enhanced service supports both:")
        logger.info("  • General conversation (when MCP tools aren't needed)")
        logger.info("  • Airline booking tasks (using MCP tools when available)")
        logger.info("  • Graceful fallback when MCP tools are unavailable")


if __name__ == "__main__":
    try:
        asyncio.run(test_simple_chat_with_mcp())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

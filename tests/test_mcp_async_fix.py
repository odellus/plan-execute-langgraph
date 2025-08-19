#!/usr/bin/env python3
"""
Quick test to verify MCP async issues are resolved.
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
logger = logging.getLogger("async_fix_test")


async def test_mcp_async_fix():
    """Test that MCP tools now work properly with async calls."""
    logger.info("🧪 Testing MCP Async Fix")
    
    # Create connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        # Initialize the enhanced DSPy service
        service = DSPyAgentService(pool)
        await service.initialize()
        
        if service.mcp_tools:
            logger.info(f"✓ Service initialized with {len(service.mcp_tools)} MCP tools")
            
            # Test a flight search that should work now
            request = ChatRequest(
                thread_id="async-fix-test",
                message="Find flights from SFO to Boston on December 19th, 2024"
            )
            
            logger.info("Testing flight search with fixed async tools...")
            response = await service.chat(request)
            logger.info(f"Response: {response.response}")
            
            # Check if we got a proper response (not an error)
            if "technical difficulties" not in response.response.lower():
                logger.info("✅ MCP tools are working correctly!")
            else:
                logger.warning("⚠️ Still having issues with MCP tools")
                
        else:
            logger.info("⚠️ No MCP tools available - check MCP installation")


if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_async_fix())
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

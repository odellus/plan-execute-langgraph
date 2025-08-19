#!/usr/bin/env python3
"""
Demo script for DSPy MCP airline booking integration.
Shows how to interact with the airline booking system using MCP tools.
"""
import asyncio
import logging
from psycopg_pool import AsyncConnectionPool

from src.plan_execute.agent.dspy_mcp_service import DSPyMCPAgentService
from src.plan_execute.agent.models import ChatRequest
from src.plan_execute.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mcp_demo")


async def demo_airline_booking():
    """Demonstrate airline booking capabilities."""
    logger.info("🛫 Starting MCP Airline Booking Demo")
    
    # Create connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        # Initialize the MCP service
        service = DSPyMCPAgentService(pool)
        await service.initialize()
        logger.info("✓ DSPy MCP service initialized")
        
        # Demo scenarios
        scenarios = [
            {
                "name": "Flight Search",
                "message": "I'm looking for flights from SFO to JFK on September 1st, 2025. Can you show me what's available?"
            },
            {
                "name": "Flight Booking",
                "message": "Please book the cheapest flight from SFO to JFK on September 1st, 2025 for Adam."
            },
            {
                "name": "Itinerary Check",
                "message": "Can you check my booking details? I'm Adam and I just made a booking."
            },
            {
                "name": "User Info Lookup",
                "message": "Can you look up information for user Bob?"
            },
            {
                "name": "Complex Request",
                "message": "Hi, I'm Chelsie. I need to book a round trip from SFO to JFK. I want to leave on September 1st and return on September 2nd, 2025. Please find me the best options."
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Demo Scenario {i}: {scenario['name']}")
            logger.info(f"{'='*60}")
            logger.info(f"User: {scenario['message']}")
            logger.info(f"{'-'*60}")
            
            # Create request
            request = ChatRequest(
                thread_id=f"demo-thread-{i}",
                message=scenario['message']
            )
            
            try:
                # Get response
                response = await service.chat(request)
                logger.info(f"Assistant: {response.response}")
                
            except Exception as e:
                logger.error(f"❌ Error in scenario {i}: {e}")
            
            # Small delay between scenarios
            await asyncio.sleep(2)
        
        logger.info(f"\n{'='*60}")
        logger.info("🎉 Demo completed! The MCP airline booking system is working.")
        logger.info("Available tools demonstrated:")
        logger.info("  • fetch_flight_info - Search for available flights")
        logger.info("  • book_itinerary - Book flights for users")
        logger.info("  • fetch_itinerary - Check booking details")
        logger.info("  • get_user_info - Look up user information")
        logger.info("  • modify_itinerary - Change or cancel bookings")
        logger.info("  • file_ticket - Create support tickets")


async def demo_streaming():
    """Demonstrate streaming responses."""
    logger.info("\n🌊 Starting Streaming Demo")
    
    # Create connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        # Initialize the MCP service
        service = DSPyMCPAgentService(pool)
        await service.initialize()
        
        # Stream a complex booking request
        request = ChatRequest(
            thread_id="streaming-demo",
            message="Hi! I'm David and I need help booking a flight from LAX to JFK on September 1st, 2025. Please search for flights and book the best one for me."
        )
        
        logger.info(f"User: {request.message}")
        logger.info("Assistant (streaming):")
        
        # Collect the full response
        full_response = ""
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
                                full_response += content
                    except json.JSONDecodeError:
                        pass
        
        print()  # New line after streaming
        logger.info("✓ Streaming demo completed")


if __name__ == "__main__":
    async def main():
        try:
            await demo_airline_booking()
            await demo_streaming()
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    asyncio.run(main())

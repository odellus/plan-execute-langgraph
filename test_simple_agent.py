#!/usr/bin/env python3
"""
Simple test script to verify the simple agent functionality.
"""

import asyncio
import sys
import os

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plan_execute.agent.simple_service import SimpleAgentService
from plan_execute.agent.models import ChatRequest
from plan_execute.config import settings
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_agent():
    """Test the simple agent with a basic message."""
    print("Testing Simple Agent...")
    
    # Create a mock connection pool for testing
    # In a real scenario, this would be a real PostgreSQL connection pool
    class MockPool:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    try:
        # Create the service with a mock pool
        service = SimpleAgentService(MockPool())
        
        # Test message
        test_request = ChatRequest(
            message="Hello! Can you help me with a simple test?",
            thread_id="test-thread"
        )
        
        print(f"Sending message: {test_request.message}")
        
        # Test non-streaming chat
        response = await service.chat(test_request)
        print(f"Response: {response.response}")
        
        # Test streaming chat
        print("\nTesting streaming response...")
        async for chunk in service.chat_stream(test_request):
            print(f"Stream chunk: {chunk.strip()}")
        
        print("\n✅ Simple agent test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_fastapi_endpoints():
    """Test the FastAPI endpoints."""
    print("\nTesting FastAPI Endpoints...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient(base_url="http://localhost:8032") as client:
            # Test the simple chat endpoint
            test_request = {"message": "Hello from test!", "thread_id": "test-thread"}
            
            print("Testing /simple-chat endpoint...")
            response = await client.post("/simple-chat", json=test_request)
            if response.status_code == 200:
                print(f"✅ /simple-chat endpoint working: {response.json()}")
            else:
                print(f"❌ /simple-chat endpoint failed: {response.status_code}")
                return False
            
            # Test the streaming endpoint
            print("Testing /simple-chat-stream endpoint...")
            response = await client.post("/simple-chat-stream", json=test_request)
            if response.status_code == 200:
                print("✅ /simple-chat-stream endpoint working (streaming)")
                # Read the stream
                async for chunk in response.aiter_bytes():
                    print(f"Stream data: {chunk.decode()}")
                    if b'[DONE]' in chunk:
                        break
            else:
                print(f"❌ /simple-chat-stream endpoint failed: {response.status_code}")
                return False
        
        print("\n✅ FastAPI endpoints test completed successfully!")
        return True
        
    except ImportError:
        print("⚠️  httpx not available, skipping FastAPI endpoint test")
        return True
    except Exception as e:
        print(f"❌ FastAPI endpoints test failed: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Starting Simple Agent Tests")
    print("=" * 50)
    
    # Test the simple agent
    agent_success = await test_simple_agent()
    
    # Test FastAPI endpoints
    endpoint_success = await test_fastapi_endpoints()
    
    print("\n" + "=" * 50)
    if agent_success and endpoint_success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
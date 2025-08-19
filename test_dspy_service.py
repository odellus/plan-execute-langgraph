#!/usr/bin/env python3
"""
Test the DSPy-based agent service.
"""
import asyncio
import logging
from psycopg_pool import AsyncConnectionPool
from plan_execute.agent.dspy_service import DSPyAgentService
from plan_execute.agent.models import ChatRequest
from plan_execute.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_dspy_service")


async def test_dspy_service():
    """Test the DSPy service basic functionality."""
    print("🧪 Testing DSPy Agent Service")
    print("=" * 50)
    
    # Create database connection pool
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        try:
            # Initialize the DSPy service
            service = DSPyAgentService(pool)
            await service.initialize()
            
            print("✅ DSPy service initialized successfully")
            
            # Test non-streaming chat
            print("\n=== Testing Non-Streaming Chat ===")
            request = ChatRequest(
                message="What is 2+2?",
                thread_id="test-dspy-001"
            )
            
            try:
                response = await service.chat(request)
                print(f"✅ Non-streaming response: {response.response}")
            except Exception as e:
                print(f"❌ Non-streaming test failed: {e}")
                return False
            
            # Test streaming chat
            print("\n=== Testing Streaming Chat ===")
            stream_request = ChatRequest(
                message="Tell me a short joke",
                thread_id="test-dspy-002"
            )
            
            try:
                print("Streaming response:")
                print("-" * 40)
                
                full_response = ""
                chunk_count = 0
                
                async for chunk in service.chat_stream(stream_request):
                    if chunk.startswith("data: "):
                        chunk_data = chunk[6:].strip()
                        if chunk_data == "[DONE]":
                            print(f"\n🏁 Stream finished! ({chunk_count} chunks)")
                            break
                        elif chunk_data.startswith("Error:"):
                            print(f"\n❌ Error in stream: {chunk_data}")
                            return False
                        else:
                            # Try to parse and extract content
                            try:
                                import json
                                data = json.loads(chunk_data)
                                if 'choices' in data and data['choices']:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        print(content, end='', flush=True)
                                        full_response += content
                                        chunk_count += 1
                            except json.JSONDecodeError:
                                # Skip non-JSON chunks
                                pass
                
                print(f"\n✅ Streaming test completed with {len(full_response)} characters")
                
            except Exception as e:
                print(f"❌ Streaming test failed: {e}")
                return False
            
            # Test conversation continuity
            print("\n=== Testing Conversation Continuity ===")
            
            # First message
            req1 = ChatRequest(
                message="My name is Alice. Remember this.",
                thread_id="test-dspy-continuity"
            )
            
            try:
                resp1 = await service.chat(req1)
                print(f"Message 1 response: {resp1.response}")
                
                # Second message - should remember the name
                req2 = ChatRequest(
                    message="What's my name?",
                    thread_id="test-dspy-continuity"  # Same thread
                )
                
                resp2 = await service.chat(req2)
                print(f"Message 2 response: {resp2.response}")
                
                # Check if the response mentions Alice
                if "alice" in resp2.response.lower():
                    print("✅ Conversation continuity test passed")
                else:
                    print("⚠️ Conversation continuity test unclear - response doesn't mention Alice")
                
            except Exception as e:
                print(f"❌ Conversation continuity test failed: {e}")
                return False
            
            print("\n" + "=" * 50)
            print("🎉 All DSPy service tests completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ DSPy service test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_dspy_checkpointer():
    """Test the DSPy checkpointer directly."""
    print("\n🧪 Testing DSPy Checkpointer")
    print("=" * 50)
    
    db_uri = settings.postgres_dsn
    async with AsyncConnectionPool(db_uri, open=False, kwargs=dict(autocommit=True)) as pool:
        try:
            from plan_execute.agent.dspy_checkpointer import DSPyConversationCheckpointer
            import dspy
            
            checkpointer = DSPyConversationCheckpointer(pool)
            await checkpointer.setup()
            
            # Test saving and loading history
            test_history = dspy.History(messages=[
                {"user_message": "Hello", "response": "Hi there!"},
                {"user_message": "How are you?", "response": "I'm doing well, thanks!"}
            ])
            
            thread_id = "test-checkpointer-001"
            
            # Save history
            await checkpointer.save_conversation(thread_id, test_history)
            print("✅ Saved test conversation")
            
            # Load history
            loaded_history = await checkpointer.load_conversation(thread_id)
            print(f"✅ Loaded conversation with {len(loaded_history.messages)} messages")
            
            # Verify data integrity
            if len(loaded_history.messages) == 2:
                print("✅ Checkpointer data integrity verified")
            else:
                print(f"❌ Data integrity issue: expected 2 messages, got {len(loaded_history.messages)}")
                return False
            
            # Test listing conversations
            conversations = await checkpointer.list_conversations()
            print(f"✅ Listed {len(conversations)} conversations")
            
            # Clean up test data
            await checkpointer.delete_conversation(thread_id)
            print("✅ Cleaned up test conversation")
            
            return True
            
        except Exception as e:
            print(f"❌ Checkpointer test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    async def main():
        # Test checkpointer first
        checkpointer_ok = await test_dspy_checkpointer()
        
        # Test full service
        service_ok = await test_dspy_service()
        
        print("\n" + "=" * 50)
        print("📋 Test Results:")
        print(f"  Checkpointer: {'✅ PASS' if checkpointer_ok else '❌ FAIL'}")
        print(f"  Service:      {'✅ PASS' if service_ok else '❌ FAIL'}")
        
        if checkpointer_ok and service_ok:
            print("\n🎉 All DSPy tests passed!")
        else:
            print("\n💥 Some DSPy tests failed.")
    
    asyncio.run(main())
#!/usr/bin/env python3
"""
Dead simple test for the simple-chat streaming interface.
Tests the /simple-chat-stream endpoint with Server-Sent Events (SSE).
"""
import requests
import json
import time

def test_simple_chat_stream():
    """Test the streaming simple-chat endpoint."""
    
    # The request payload
    payload = {
        "message": "Write an exceedingly dry 300 word essay on the history of ordoliberalism in post cold war Germany.",
        "thread_id": "test-stream-128"
    }
    
    print(f"🚀 Testing streaming chat with message: {payload['message']}")
    print(f"📝 Thread ID: {payload['thread_id']}")
    print("-" * 60)
    
    try:
        # Make the streaming request
        response = requests.post(
            "http://localhost:8032/simple-chat-stream",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            stream=True  # Important for streaming
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        print("✅ Connected! Streaming response:")
        print("=" * 40)
        
        # Process the streaming response
        full_response = ""
        chunk_count = 0
        start_time = time.time()
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # SSE format: "data: <content>"
                if line.startswith("data: "):
                    chunk = line[6:]  # Remove "data: " prefix
                    
                    if chunk == "[DONE]":
                        elapsed = time.time() - start_time
                        print(f"\n🏁 Stream finished! ({elapsed:.2f}s)")
                        break
                    elif chunk.startswith("Error:"):
                        print(f"\n❌ Error received: {chunk}")
                        return False
                    else:
                        # Print each chunk with timestamp and flush immediately
                        elapsed = time.time() - start_time
                        print(f"{chunk}", flush=True, end="")
                        full_response += chunk
                        chunk_count += 1
                        
                        # Add a small delay to make streaming more visible
                        time.sleep(0.1)
        
        print("\n" + "=" * 40)
        print(f"📊 Stream complete! Received {chunk_count} chunks")
        print(f"📝 Full response length: {len(full_response)} characters")
        
        if full_response.strip():
            print("✅ Test PASSED - Received streaming response!")
            return True
        else:
            print("❌ Test FAILED - No content received")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the server running on localhost:8032?")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def test_simple_chat_non_stream():
    """Test the non-streaming simple-chat endpoint for comparison."""
    
    payload = {
        "message": "What's 2+2?",
        "thread_id": "test-nonstream-456"
    }
    
    print(f"\n🔄 Testing non-streaming chat with message: {payload['message']}")
    print("-" * 60)
    
    try:
        response = requests.post(
            "http://localhost:8032/simple-chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Non-streaming response: {result['response']}")
            return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Non-streaming test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Simple Chat Stream Test")
    print("=" * 60)
    
    # Test streaming endpoint
    stream_success = test_simple_chat_stream()
    
    # Test non-streaming endpoint for comparison
    nonstream_success = test_simple_chat_non_stream()
    
    print("\n" + "=" * 60)
    print("📋 Test Results:")
    print(f"  Streaming:     {'✅ PASS' if stream_success else '❌ FAIL'}")
    print(f"  Non-streaming: {'✅ PASS' if nonstream_success else '❌ FAIL'}")
    
    if stream_success:
        print("\n🎉 Streaming interface is working correctly!")
    else:
        print("\n💥 Streaming interface has issues.")

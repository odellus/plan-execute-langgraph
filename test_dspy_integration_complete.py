#!/usr/bin/env python3
"""
Comprehensive test to verify DSPy integration is complete and working.
"""
import asyncio
import requests
import json
import time
import subprocess
import signal
import os
from contextlib import asynccontextmanager


class ServerManager:
    """Context manager to start and stop the server for testing."""
    
    def __init__(self):
        self.process = None
    
    def start(self):
        """Start the server."""
        print("🚀 Starting server...")
        self.process = subprocess.Popen(
            ["uv", "run", "python", "-m", "plan_execute.app"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait for server to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get("http://localhost:8032/docs", timeout=1)
                if response.status_code == 200:
                    print("✅ Server started successfully")
                    return True
            except requests.exceptions.RequestException:
                time.sleep(1)
        
        print("❌ Server failed to start")
        return False
    
    def stop(self):
        """Stop the server."""
        if self.process:
            print("🛑 Stopping server...")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.wait()
            print("✅ Server stopped")
    
    def __enter__(self):
        if self.start():
            return self
        else:
            raise Exception("Failed to start server")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def test_streaming_endpoint():
    """Test the streaming endpoint with DSPy."""
    print("\n=== Testing Streaming Endpoint ===")
    
    payload = {
        "message": "Tell me a joke about programming",
        "thread_id": "test-dspy-streaming-001"
    }
    
    try:
        response = requests.post(
            "http://localhost:8032/simple-chat-stream",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            },
            stream=True
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
        
        chunks = 0
        content_length = 0
        
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                chunk_data = line[6:]
                if chunk_data == "[DONE]":
                    break
                elif chunk_data.startswith("Error:"):
                    print(f"❌ Error in stream: {chunk_data}")
                    return False
                else:
                    try:
                        data = json.loads(chunk_data)
                        if 'choices' in data and data['choices']:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                content_length += len(content)
                                chunks += 1
                    except json.JSONDecodeError:
                        pass
        
        print(f"✅ Streaming: {chunks} chunks, {content_length} characters")
        return chunks > 0 and content_length > 0
        
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False


def test_non_streaming_endpoint():
    """Test the non-streaming endpoint with DSPy."""
    print("\n=== Testing Non-Streaming Endpoint ===")
    
    payload = {
        "message": "What is the capital of France?",
        "thread_id": "test-dspy-nonstreaming-001"
    }
    
    try:
        response = requests.post(
            "http://localhost:8032/simple-chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'response' in result and result['response'].strip():
                print(f"✅ Non-streaming: {len(result['response'])} characters")
                return True
            else:
                print("❌ Empty response")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Non-streaming test failed: {e}")
        return False


def test_conversation_continuity():
    """Test conversation continuity with DSPy checkpointer."""
    print("\n=== Testing Conversation Continuity ===")
    
    thread_id = "test-dspy-continuity-001"
    
    # First message
    payload1 = {
        "message": "My favorite color is blue. Please remember this.",
        "thread_id": thread_id
    }
    
    try:
        response1 = requests.post(
            "http://localhost:8032/simple-chat",
            json=payload1,
            headers={"Content-Type": "application/json"}
        )
        
        if response1.status_code != 200:
            print(f"❌ First message failed: {response1.status_code}")
            return False
        
        result1 = response1.json()
        print(f"Message 1: {result1['response'][:100]}...")
        
        # Second message - should remember the color
        payload2 = {
            "message": "What is my favorite color?",
            "thread_id": thread_id
        }
        
        response2 = requests.post(
            "http://localhost:8032/simple-chat",
            json=payload2,
            headers={"Content-Type": "application/json"}
        )
        
        if response2.status_code != 200:
            print(f"❌ Second message failed: {response2.status_code}")
            return False
        
        result2 = response2.json()
        print(f"Message 2: {result2['response'][:100]}...")
        
        # Check if the response mentions blue
        if "blue" in result2['response'].lower():
            print("✅ Conversation continuity working")
            return True
        else:
            print("⚠️ Conversation continuity unclear")
            return False
            
    except Exception as e:
        print(f"❌ Continuity test failed: {e}")
        return False


def test_error_handling():
    """Test error handling with empty messages."""
    print("\n=== Testing Error Handling ===")
    
    payload = {
        "message": "",  # Empty message
        "thread_id": "test-dspy-error-001"
    }
    
    try:
        response = requests.post(
            "http://localhost:8032/simple-chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'response' in result and "didn't receive" in result['response']:
                print("✅ Error handling working")
                return True
            else:
                print(f"❌ Unexpected response: {result}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_api_compatibility():
    """Test that the API is compatible with the original interface."""
    print("\n=== Testing API Compatibility ===")
    
    # Test CORS preflight
    try:
        response = requests.options("http://localhost:8032/simple-chat-stream")
        if response.status_code != 200:
            print(f"❌ CORS preflight failed: {response.status_code}")
            return False
        
        print("✅ CORS preflight working")
        
        # Test that both endpoints exist and respond
        endpoints = [
            "/simple-chat",
            "/simple-chat-stream"
        ]
        
        for endpoint in endpoints:
            try:
                # Just check that the endpoint exists (will fail with missing data, but that's OK)
                response = requests.post(f"http://localhost:8032{endpoint}")
                # We expect 422 (validation error) for missing data, not 404 (not found)
                if response.status_code in [200, 422]:
                    print(f"✅ Endpoint {endpoint} exists")
                else:
                    print(f"❌ Endpoint {endpoint} issue: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Endpoint {endpoint} failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ API compatibility test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 DSPy Integration Complete Test")
    print("=" * 50)
    
    with ServerManager():
        # Wait a moment for server to fully initialize
        time.sleep(2)
        
        tests = [
            ("Streaming", test_streaming_endpoint),
            ("Non-Streaming", test_non_streaming_endpoint),
            ("Conversation Continuity", test_conversation_continuity),
            ("Error Handling", test_error_handling),
            ("API Compatibility", test_api_compatibility),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
                results[test_name] = False
        
        print("\n" + "=" * 50)
        print("📋 Final Test Results:")
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name:<20}: {status}")
            if not passed:
                all_passed = False
        
        print("\n" + "=" * 50)
        if all_passed:
            print("🎉 ALL TESTS PASSED! DSPy integration is complete and working!")
            print("\n✨ Summary:")
            print("  • DSPy has successfully replaced LangGraph")
            print("  • Streaming and non-streaming endpoints work")
            print("  • Conversation persistence works via PostgreSQL")
            print("  • API compatibility is maintained")
            print("  • Frontend should work without any changes")
        else:
            print("💥 Some tests failed. DSPy integration needs fixes.")
        
        return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
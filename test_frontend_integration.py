#!/usr/bin/env python3
"""
Test script to verify the frontend-backend integration.
This script tests the backend streaming endpoint directly.
"""

import requests
import json
import time

def test_backend_streaming():
    """Test the backend streaming endpoint directly."""
    print("Testing backend streaming endpoint...")
    
    url = 'http://localhost:8032/simple-chat-stream'
    data = {
        'message': 'Hello! Can you tell me a short joke?',
        'thread_id': f'test-thread-{int(time.time())}'
    }
    
    try:
        response = requests.post(url, json=data, stream=True, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
            return False
            
        print("Streaming response:")
        full_text = ""
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                
                if data_str == '[DONE]':
                    print("Stream completed.")
                    break
                    
                try:
                    chunk_data = json.loads(data_str)
                    content = chunk_data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                    if content:
                        full_text += content
                        print(f"Received: {repr(content)}")
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON: {repr(data_str)}")
        
        print(f"\nFull response: {repr(full_text)}")
        return len(full_text) > 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_backend_non_streaming():
    """Test the non-streaming endpoint for comparison."""
    print("\nTesting non-streaming endpoint...")
    
    url = 'http://localhost:8032/simple-chat'
    data = {
        'message': 'Hello! This is a test.',
        'thread_id': f'test-thread-{int(time.time())}'
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Starting backend integration tests...\n")
    
    # Test streaming endpoint
    streaming_success = test_backend_streaming()
    
    # Test non-streaming endpoint
    non_streaming_success = test_backend_non_streaming()
    
    print(f"\nResults:")
    print(f"Streaming endpoint: {'✓ PASS' if streaming_success else '✗ FAIL'}")
    print(f"Non-streaming endpoint: {'✓ PASS' if non_streaming_success else '✗ FAIL'}")
    
    if streaming_success and non_streaming_success:
        print("\n🎉 All tests passed! Backend is ready for frontend integration.")
    else:
        print("\n❌ Some tests failed. Check the backend configuration.")
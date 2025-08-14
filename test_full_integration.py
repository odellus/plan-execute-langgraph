#!/usr/bin/env python3
"""
Comprehensive integration test for the frontend-backend setup.
This tests the streaming endpoint with conversation continuity.
"""

import requests
import json
import time
import uuid

def test_conversation_continuity():
    """Test that the backend maintains conversation context across multiple messages."""
    print("Testing conversation continuity...")
    
    thread_id = f"test-conversation-{uuid.uuid4()}"
    base_url = 'http://localhost:8032/simple-chat-stream'
    
    messages = [
        "Hi, my name is Alice. Please remember it.",
        "What's my name?",
        "Can you tell me a joke about my name?"
    ]
    
    responses = []
    
    for i, message in enumerate(messages):
        print(f"\n--- Message {i+1}: {message} ---")
        
        data = {
            'message': message,
            'thread_id': thread_id
        }
        
        try:
            response = requests.post(base_url, json=data, stream=True, timeout=30)
            
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                return False
            
            full_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data: '):
                    data_str = line[6:].strip()
                    
                    if data_str == '[DONE]':
                        break
                    
                    if data_str == '':
                        continue
                        
                    try:
                        chunk_data = json.loads(data_str)
                        content = chunk_data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            full_text += content
                    except json.JSONDecodeError:
                        pass
            
            responses.append(full_text)
            print(f"Response: {full_text}")
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    # Check if the assistant remembered the name
    if len(responses) >= 2:
        second_response = responses[1].lower()
        if "alice" in second_response:
            print("\n✅ Conversation continuity test PASSED - Assistant remembered the name!")
            return True
        else:
            print(f"\n❌ Conversation continuity test FAILED - Assistant didn't remember the name.")
            print(f"Second response: {responses[1]}")
            return False
    
    return False

def test_streaming_performance():
    """Test streaming performance and chunk delivery."""
    print("\nTesting streaming performance...")
    
    data = {
        'message': 'Please write a short story about a robot learning to paint. Make it about 200 words.',
        'thread_id': f'perf-test-{uuid.uuid4()}'
    }
    
    start_time = time.time()
    first_chunk_time = None
    total_chunks = 0
    total_characters = 0
    
    try:
        response = requests.post('http://localhost:8032/simple-chat-stream', json=data, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            return False
        
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                data_str = line[6:].strip()
                
                if data_str == '[DONE]':
                    break
                
                if data_str == '':
                    continue
                    
                try:
                    chunk_data = json.loads(data_str)
                    content = chunk_data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                    if content:
                        if first_chunk_time is None:
                            first_chunk_time = time.time()
                        total_chunks += 1
                        total_characters += len(content)
                except json.JSONDecodeError:
                    pass
        
        end_time = time.time()
        
        if first_chunk_time:
            time_to_first_chunk = first_chunk_time - start_time
            total_time = end_time - start_time
            
            print(f"Time to first chunk: {time_to_first_chunk:.2f}s")
            print(f"Total streaming time: {total_time:.2f}s")
            print(f"Total chunks: {total_chunks}")
            print(f"Total characters: {total_characters}")
            print(f"Average characters per chunk: {total_characters/total_chunks:.1f}")
            
            if time_to_first_chunk < 5.0 and total_chunks > 5:
                print("✅ Streaming performance test PASSED")
                return True
            else:
                print("❌ Streaming performance test FAILED - Too slow or too few chunks")
                return False
        else:
            print("❌ No chunks received")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_error_handling():
    """Test error handling with invalid requests."""
    print("\nTesting error handling...")
    
    # Test with empty message
    try:
        response = requests.post('http://localhost:8032/simple-chat-stream', 
                               json={'message': '', 'thread_id': 'test'}, 
                               timeout=10)
        if response.status_code == 200:
            print("✅ Empty message handled gracefully")
        else:
            print(f"❌ Empty message returned error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error with empty message: {e}")
        return False
    
    # Test with missing fields
    try:
        response = requests.post('http://localhost:8032/simple-chat-stream', 
                               json={'message': 'test'}, 
                               timeout=10)
        if response.status_code in [200, 422]:  # 422 is validation error, which is expected
            print("✅ Missing thread_id handled appropriately")
        else:
            print(f"❌ Missing thread_id returned unexpected error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error with missing thread_id: {e}")
        return False
    
    return True

def main():
    """Run all integration tests."""
    print("🚀 Starting comprehensive integration tests...\n")
    
    tests = [
        ("Conversation Continuity", test_conversation_continuity),
        ("Streaming Performance", test_streaming_performance),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The frontend-backend integration is working perfectly.")
        return True
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
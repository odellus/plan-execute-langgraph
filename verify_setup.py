#!/usr/bin/env python3
"""
Final verification script to ensure the frontend-backend integration is ready.
"""

import requests
import subprocess
import time
import json
import sys

def check_backend():
    """Check if backend is running and responding."""
    try:
        response = requests.get('http://localhost:8032/docs', timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running on http://localhost:8032")
            return True
        else:
            print("❌ Backend is not responding correctly")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running on http://localhost:8032")
        print("   Start it with: uv run python src/plan_execute/app.py")
        return False
    except Exception as e:
        print(f"❌ Backend check failed: {e}")
        return False

def check_frontend():
    """Check if frontend is running."""
    try:
        response = requests.get('http://localhost:3004', timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is running on http://localhost:3004")
            return True
        else:
            print("❌ Frontend is not responding correctly")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Frontend is not running on http://localhost:3004")
        print("   Start it with: cd frontend && npm run dev")
        return False
    except Exception as e:
        print(f"❌ Frontend check failed: {e}")
        return False

def test_streaming_endpoint():
    """Test the streaming endpoint with a simple message."""
    print("\n🧪 Testing streaming endpoint...")
    
    try:
        data = {
            'message': 'Hello! This is a verification test.',
            'thread_id': f'verify-{int(time.time())}'
        }
        
        response = requests.post('http://localhost:8032/simple-chat-stream', 
                               json=data, stream=True, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Streaming endpoint returned status {response.status_code}")
            return False
        
        content_received = False
        for line in response.iter_lines(decode_unicode=True):
            if line.startswith('data: '):
                data_str = line[6:].strip()
                if data_str == '[DONE]':
                    break
                if data_str and data_str != '':
                    try:
                        chunk_data = json.loads(data_str)
                        content = chunk_data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            content_received = True
                            break
                    except json.JSONDecodeError:
                        pass
        
        if content_received:
            print("✅ Streaming endpoint is working correctly")
            return True
        else:
            print("❌ No content received from streaming endpoint")
            return False
            
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False

def check_files():
    """Check if all required files are in place."""
    print("\n📁 Checking required files...")
    
    required_files = [
        'frontend/app/runtime-provider.tsx',
        'frontend/app/assistant.tsx',
        'src/plan_execute/app.py',
        'src/plan_execute/agent/simple_service.py'
    ]
    
    all_present = True
    for file_path in required_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if file_path == 'frontend/app/runtime-provider.tsx':
                    if 'MyModelAdapter' in content and 'useLocalRuntime' in content:
                        print(f"✅ {file_path}")
                    else:
                        print(f"❌ {file_path} - Missing required components")
                        all_present = False
                elif file_path == 'frontend/app/assistant.tsx':
                    if 'MyRuntimeProvider' in content:
                        print(f"✅ {file_path}")
                    else:
                        print(f"❌ {file_path} - Not using MyRuntimeProvider")
                        all_present = False
                else:
                    print(f"✅ {file_path}")
        except FileNotFoundError:
            print(f"❌ {file_path} - File not found")
            all_present = False
    
    return all_present

def main():
    """Run all verification checks."""
    print("🔍 Verifying Frontend-Backend Integration Setup")
    print("=" * 50)
    
    checks = [
        ("Required Files", check_files),
        ("Backend Service", check_backend),
        ("Frontend Service", check_frontend),
        ("Streaming Endpoint", test_streaming_endpoint),
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        result = check_func()
        results.append((check_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} checks")
    
    if passed == len(results):
        print("\n🎉 SUCCESS! Your frontend-backend integration is ready!")
        print("\n📝 Next steps:")
        print("1. Open http://localhost:3004 in your browser")
        print("2. Send a message to test the streaming chat")
        print("3. Verify conversation continuity by asking follow-up questions")
        print("4. Check the browser console for debug logs")
        return True
    else:
        print(f"\n⚠️ {len(results) - passed} check(s) failed.")
        print("Please fix the issues above before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
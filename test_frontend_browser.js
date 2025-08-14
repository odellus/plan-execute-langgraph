// Simple browser test to verify the frontend integration
// Run this in the browser console when on localhost:3004

async function testFrontendIntegration() {
    console.log("🧪 Testing Frontend Integration...");
    
    // Test the backend directly from the browser
    try {
        const response = await fetch('http://localhost:8032/simple-chat-stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: 'Hello from browser test!',
                thread_id: 'browser-test-' + Date.now()
            })
        });
        
        console.log('✅ Backend connection successful:', response.status);
        
        if (response.ok) {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let text = '';
            let chunks = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr === '[DONE]') {
                            console.log('✅ Stream completed successfully');
                            console.log('📝 Full response:', text);
                            console.log('📊 Total chunks:', chunks);
                            return true;
                        }
                        
                        if (dataStr && dataStr !== '') {
                            try {
                                const data = JSON.parse(dataStr);
                                const content = data.choices?.[0]?.delta?.content;
                                if (content) {
                                    text += content;
                                    chunks++;
                                }
                            } catch (e) {
                                // Skip invalid JSON
                            }
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error('❌ Frontend integration test failed:', error);
        return false;
    }
}

// Instructions for manual testing
console.log(`
🔧 Frontend Integration Test Instructions:

1. Make sure both servers are running:
   - Backend: http://localhost:8032 
   - Frontend: http://localhost:3004

2. Open http://localhost:3004 in your browser

3. Run this test in the browser console:
   testFrontendIntegration()

4. Try sending a message in the UI to test the full integration

5. Check the browser's Network tab to see the streaming requests

Expected behavior:
- Messages should stream in real-time
- Conversation history should be maintained
- The UI should be responsive and smooth
`);

// Auto-run the test if this script is loaded
if (typeof window !== 'undefined') {
    testFrontendIntegration();
}
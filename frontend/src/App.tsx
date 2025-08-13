import React from 'react'
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
} from '@assistant-ui/react'
import type { ChatModelAdapter } from '@assistant-ui/react'


interface ChatRequest {
  message: string
  thread_id?: string
}

// Custom adapter to connect to our backend
class BackendChatAdapter implements ChatModelAdapter {
  async *run(options: any): AsyncGenerator<any, void> {
    const { messages } = options
    console.log('🚀 BackendChatAdapter.run called with:', { messages, options })
    
    const lastMessage = messages[messages.length - 1]
    console.log('📩 Last message:', lastMessage)
    
    if (lastMessage.role !== 'user') {
      throw new Error('Last message must be from user')
    }

    const userText = lastMessage.content[0]?.text || ''
    console.log('💬 Extracted user text:', userText)

    const requestBody: ChatRequest = {
      message: userText,
      thread_id: 'default',
    }
    console.log('📤 Request body:', requestBody)

    try {
      console.log('🌐 Making fetch request to /api/simple-chat-stream')
      const response = await fetch('/api/simple-chat-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      console.log('📡 Response received:', { status: response.status, ok: response.ok })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No reader available')
      }

      let accumulatedContent = ''
      console.log('🔄 Starting to read stream...')

      console.log('🎯 About to start yielding directly...')
      console.log('🎬 Starting async iterator...')
      let chunkCount = 0
      while (true) {
        console.log(`⏳ About to read chunk #${chunkCount + 1}...`)
        
        // Add timeout to detect hanging reads
        const readPromise = reader.read()
        const timeoutPromise = new Promise<never>((_, reject) => 
          setTimeout(() => reject(new Error('Read timeout after 10 seconds')), 10000)
        )
        
        let done: boolean, value: Uint8Array | undefined
        try {
          const result = await Promise.race([readPromise, timeoutPromise])
          done = result.done
          value = result.value
          chunkCount++
          console.log('📖 Read chunk:', { chunkNumber: chunkCount, done, valueLength: value?.length, hasValue: !!value })
        } catch (error: any) {
          console.error('⚠️ Read error or timeout:', error)
          if (error.message.includes('timeout')) {
            console.log('🕐 The stream appears to be hanging. Your backend might not be sending data.')
            break
          }
          throw error
        }
        
        if (done) {
          console.log('✅ Stream finished')
          break
        }

        const chunk = decoder.decode(value, { stream: true })
        console.log('🔤 Decoded chunk:', JSON.stringify(chunk))
        // Handle Server-Sent Events format with double newlines
        const lines = chunk.split('\n').filter(line => line.trim() !== '')
        console.log('📝 Split into lines:', lines)

        for (const line of lines) {
          console.log('🔍 Processing line:', line)
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            console.log('📊 Extracted data:', data)
            
            if (data === '[DONE]') {
              console.log('🏁 Received [DONE] signal')
              return
            }
            
            if (data && !data.startsWith('Error:')) {
              accumulatedContent += data
              console.log('➕ Added to accumulated content. Total length:', accumulatedContent.length)
              console.log('📤 Yielding ChatModelRunResult with content:', data)
              yield {
                content: [{
                  type: 'text',
                  text: accumulatedContent
                }]
              }
            } else {
              console.log('⚠️ Skipped data (empty or error):', data)
            }
          } else {
            console.log('⏭️ Skipped line (not data):', line)
          }
        }
      }
      console.log('🔒 Releasing reader lock')
      reader.releaseLock()
    } catch (error: any) {
      console.error('Error in chat adapter:', error)
      throw error
    }
  }
}

const ChatComponent: React.FC = () => {
  const runtime = useLocalRuntime(new BackendChatAdapter())
  
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column' }}>
        <div style={{ 
          padding: '1rem', 
          borderBottom: '1px solid #333', 
          background: '#1a1a1a',
          color: 'white'
        }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Simple Chat Agent</h1>
          <p style={{ margin: '0.5rem 0 0 0', opacity: 0.7, fontSize: '0.9rem' }}>
            Powered by LangGraph + Assistant UI
          </p>
        </div>
        
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <ThreadPrimitive.Root style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <ThreadPrimitive.Viewport style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
              <ThreadPrimitive.Messages 
                components={{
                  UserMessage: () => (
                    <div style={{
                      marginBottom: '1rem',
                      padding: '0.75rem',
                      borderRadius: '0.5rem',
                      background: '#2a2a2a',
                      color: 'white',
                      maxWidth: '70%',
                      marginLeft: 'auto',
                    }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                        You
                      </div>
                      <MessagePrimitive.Content />
                    </div>
                  ),
                  AssistantMessage: () => (
                    <div style={{
                      marginBottom: '1rem',
                      padding: '0.75rem',
                      borderRadius: '0.5rem',
                      background: '#1a1a1a',
                      color: 'white',
                      maxWidth: '70%',
                      marginRight: 'auto',
                    }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                        Assistant
                      </div>
                      <MessagePrimitive.Content />
                    </div>
                  ),
                }}
              />
            </ThreadPrimitive.Viewport>
            <div style={{ padding: '1rem', borderTop: '1px solid #333', background: '#1a1a1a' }}>
              <ComposerPrimitive.Root>
                <ComposerPrimitive.Input
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #333',
                    borderRadius: '0.5rem',
                    background: '#2a2a2a',
                    color: 'white',
                    fontSize: '1rem',
                    resize: 'none',
                  }}
                  placeholder="Type your message..."
                />
                <ComposerPrimitive.Send
                  style={{
                    marginTop: '0.5rem',
                    padding: '0.75rem 1.5rem',
                    border: 'none',
                    borderRadius: '0.5rem',
                    background: '#007acc',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: 'bold',
                  }}
                >
                  Send
                </ComposerPrimitive.Send>
              </ComposerPrimitive.Root>
            </div>
          </ThreadPrimitive.Root>
        </div>
      </div>
    </AssistantRuntimeProvider>
  )
}



const App: React.FC = () => {
  return <ChatComponent />
}

export default App
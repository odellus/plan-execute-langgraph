import React, { useState, useCallback } from 'react'
import {
  AssistantRuntime,
  ChatModelAdapter,
  ThreadMessage,
  TextContentPart,
  UserMessage,
} from '@assistant-ui/react'
import { useChatRuntime } from '@assistant-ui/react'
import { MarkdownText } from '@assistant-ui/react-markdown'

interface ChatRequest {
  message: string
  thread_id?: string
}

// Custom adapter to connect to our backend
class BackendChatAdapter implements ChatModelAdapter {
  async run({
    messages,
    threadId,
  }: {
    messages: ThreadMessage[]
    threadId?: string
  }): Promise<AsyncIterable<ThreadMessage>> {
    const lastMessage = messages[messages.length - 1]
    
    if (lastMessage.role !== 'user') {
      throw new Error('Last message must be from user')
    }

    const userMessage = lastMessage as UserMessage
    const textContent = userMessage.content[0] as TextContentPart
    const userText = textContent.text

    const requestBody: ChatRequest = {
      message: userText,
      thread_id: threadId || 'default',
    }

    try {
      const response = await fetch('/api/simple-chat-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No reader available')
      }

      let accumulatedContent = ''

      return {
        async *[Symbol.asyncIterator]() {
          try {
            while (true) {
              const { done, value } = await reader.read()
              
              if (done) break

              const chunk = decoder.decode(value, { stream: true })
              const lines = chunk.split('\n')

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const data = line.slice(6)
                  
                  if (data === '[DONE]') {
                    if (accumulatedContent) {
                      yield {
                        id: Date.now().toString(),
                        role: 'assistant' as const,
                        content: [{ type: 'text' as const, text: accumulatedContent }],
                        createdAt: new Date(),
                      }
                    }
                    return
                  }
                  
                  if (data && !data.startsWith('Error:')) {
                    accumulatedContent += data
                  }
                }
              }
            }
          } finally {
            reader.releaseLock()
          }
        },
      }
    } catch (error) {
      console.error('Error in chat adapter:', error)
      throw error
    }
  }
}

const SimpleChatComponent: React.FC = () => {
  const [threadId] = useState(() => `thread_${Date.now()}`)
  
  const runtime = useChatRuntime({
    adapter: new BackendChatAdapter(),
    threadId,
  })

  return (
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
      
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <AssistantRuntime runtime={runtime}>
          <div style={{ height: '100%', width: '100%' }}>
            {/* Chat messages will be rendered here by Assistant UI */}
            <div 
              style={{ 
                height: '100%', 
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                fontFamily: 'Inter, system-ui, sans-serif'
              }}
            >
              {/* Message list */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
                {runtime.messages.map((message) => (
                  <div
                    key={message.id}
                    style={{
                      marginBottom: '1rem',
                      padding: '0.75rem',
                      borderRadius: '0.5rem',
                      background: message.role === 'user' ? '#2a2a2a' : '#1a1a1a',
                      color: 'white',
                      maxWidth: '70%',
                      marginLeft: message.role === 'user' ? 'auto' : '0',
                      marginRight: message.role === 'assistant' ? 'auto' : '0',
                    }}
                  >
                    <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                      {message.role === 'user' ? 'You' : 'Assistant'}
                    </div>
                    <div style={{ lineHeight: '1.5' }}>
                      {message.content.map((part, index) => {
                        if (part.type === 'text') {
                          return (
                            <MarkdownText key={index}>
                              {part.text}
                            </MarkdownText>
                          )
                        }
                        return null
                      })}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Input area */}
              <div style={{ 
                borderTop: '1px solid #333', 
                padding: '1rem',
                background: '#1a1a1a'
              }}>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input
                    type="text"
                    placeholder="Type your message..."
                    style={{
                      flex: 1,
                      padding: '0.75rem',
                      border: '1px solid #333',
                      borderRadius: '0.5rem',
                      background: '#2a2a2a',
                      color: 'white',
                      fontSize: '1rem',
                    }}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        const input = e.currentTarget
                        const message = input.value.trim()
                        if (message) {
                          runtime.append({
                            role: 'user',
                            content: [{ type: 'text', text: message }],
                          })
                          input.value = ''
                        }
                      }
                    }}
                  />
                  <button
                    onClick={() => {
                      const input = document.querySelector('input') as HTMLInputElement
                      const message = input?.value.trim()
                      if (message) {
                        runtime.append({
                          role: 'user',
                          content: [{ type: 'text', text: message }],
                        })
                        input.value = ''
                      }
                    }}
                    style={{
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
                  </button>
                </div>
              </div>
            </div>
          </div>
        </AssistantRuntime>
      </div>
    </div>
  )
}

const App: React.FC = () => {
  return <SimpleChatComponent />
}

export default App
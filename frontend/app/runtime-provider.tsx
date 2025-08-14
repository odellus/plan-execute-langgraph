"use client";

import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const BACKEND_URL = "http://localhost:8032";

// Thread management for conversations
let currentThreadId: string | null = null;

const createNewThread = () => {
  const threadId = `thread-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  currentThreadId = threadId;
  if (typeof window !== 'undefined') {
    localStorage.setItem('current-thread-id', threadId);
  }
  return threadId;
};

const getCurrentThreadId = () => {
  if (currentThreadId) return currentThreadId;
  
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('current-thread-id');
    if (stored) {
      currentThreadId = stored;
      return stored;
    }
  }
  
  return createNewThread();
};

// Function to start a new conversation (creates new thread)
const startNewConversation = () => {
  return createNewThread();
};

const MyModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal, context }) {
    // Extract the latest user message
    const userMessages = messages.filter(m => m.role === "user");
    const latestMessage = userMessages[userMessages.length - 1];
    
    if (!latestMessage) {
      yield {
        content: [{ type: "text", text: "No message received." }],
      };
      return;
    }

    // Use current thread ID for conversation continuity
    const threadId = getCurrentThreadId();

    try {
      console.log(`Calling backend with message:`, latestMessage.content, `and thread_id: "${threadId}"`);
      console.log(`Message type:`, typeof latestMessage.content);
      console.log(`Full latestMessage:`, latestMessage);
      
      // Extract text content if it's an array of content parts
      let messageText: string;
      if (typeof latestMessage.content === 'string') {
        messageText = latestMessage.content;
      } else if (Array.isArray(latestMessage.content)) {
        // Handle content array format from assistant-ui
        messageText = latestMessage.content
          .filter(part => part.type === 'text')
          .map(part => part.text)
          .join('');
      } else {
        messageText = String(latestMessage.content);
      }
      
      console.log(`Extracted messageText: "${messageText}"`);
      
      const requestBody = {
        message: messageText,
        thread_id: threadId,
      };
      
      console.log(`Request body:`, requestBody);
      
      // Call our FastAPI streaming endpoint
      const response = await fetch(`${BACKEND_URL}/simple-chat-stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
        signal: abortSignal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error("No response body");
      }

      // Parse the SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let text = "";
      let buffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || "";
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim(); // Remove 'data: ' prefix and trim
              
              if (dataStr === '[DONE]') {
                console.log("Stream completed");
                return;
              }
              
              if (dataStr === '') {
                continue; // Skip empty data lines
              }
              
              try {
                const data = JSON.parse(dataStr);
                const content = data.choices?.[0]?.delta?.content;
                
                if (content) {
                  text += content;
                  console.log(`Received content: "${content}"`);
                  
                  yield {
                    content: [{ type: "text", text }],
                  };
                }
              } catch (e) {
                // Skip invalid JSON chunks
                console.warn("Failed to parse chunk:", dataStr, e);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error("Error calling backend:", error);
      
      if (error instanceof Error && error.name === 'AbortError') {
        console.log("Request was aborted");
        return;
      }
      
      yield {
        content: [{ 
          type: "text", 
          text: `Error connecting to backend: ${error instanceof Error ? error.message : 'Unknown error'}` 
        }],
      };
    }
  },
};

export function MyRuntimeProvider({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const runtime = useLocalRuntime(MyModelAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}

// Export thread management functions for use in UI components
export { startNewConversation, getCurrentThreadId };
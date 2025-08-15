"use client";

import React, { useState, useRef, useEffect } from "react";
import { useCanvasContext } from "@/contexts/canvas-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Send, Minimize2, Maximize2 } from "lucide-react";
import { ArtifactV3, ArtifactCodeV3, ArtifactMarkdownV3, ProgrammingLanguageOptions } from "@/types";

interface CanvasChatInterfaceProps {
  chatCollapsed: boolean;
  setChatCollapsed: (collapsed: boolean) => void;
}

export const CanvasChatInterface: React.FC<CanvasChatInterfaceProps> = ({
  chatCollapsed,
  setChatCollapsed,
}) => {
  const { state, addMessage, setArtifact } = useCanvasContext();
  const { messages, artifact } = state;
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setIsLoading(true);

    // Add user message
    addMessage(userMessage, "user");

    try {
      // Call the canvas API
      const response = await fetch("/api/canvas/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage,
          artifact: artifact,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data = await response.json();
      
      // Add assistant response
      addMessage(data.message, "assistant", data.artifact);
      
      // Update artifact if provided
      if (data.artifact) {
        setArtifact(data.artifact);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      addMessage("Sorry, I encountered an error. Please try again.", "assistant");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <h2 className="font-medium">Canvas Chat</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setChatCollapsed(!chatCollapsed)}
        >
          {chatCollapsed ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] p-3 rounded-lg ${
                message.role === "user"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <div className="text-sm">{message.content}</div>
              {message.artifact && (
                <div className="mt-2 pt-2 border-t border-gray-300">
                  <div className="text-xs opacity-75">
                    Created: {message.artifact.contents[message.artifact.currentIndex - 1]?.title}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-900 p-3 rounded-lg">
              <div className="text-sm">Thinking...</div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t bg-white">
        <div className="flex space-x-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me to create or modify content..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            size="sm"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};
"use client";

import React, { createContext, useContext, useState, ReactNode } from "react";
import { v4 as uuidv4 } from "uuid";
import { 
  ArtifactV3, 
  CanvasMessage, 
  CanvasState, 
  CodeHighlight, 
  TextHighlight, 
  SearchResult,
  ProgrammingLanguageOptions
} from "@/types";

interface CanvasContextType {
  state: CanvasState;
  setArtifact: (artifact: ArtifactV3) => void;
  addMessage: (content: string, role: "user" | "assistant", artifact?: ArtifactV3) => void;
  setHighlightedCode: (highlight?: CodeHighlight) => void;
  setHighlightedText: (highlight?: TextHighlight) => void;
  setWebSearchResults: (results?: SearchResult[]) => void;
  setIsEditing: (editing: boolean) => void;
  setChatStarted: (started: boolean) => void;
  clearCanvas: () => void;
}

const CanvasContext = createContext<CanvasContextType | undefined>(undefined);

export const useCanvasContext = () => {
  const context = useContext(CanvasContext);
  if (!context) {
    throw new Error("useCanvasContext must be used within a CanvasProvider");
  }
  return context;
};

interface CanvasProviderProps {
  children: ReactNode;
}

export const CanvasProvider: React.FC<CanvasProviderProps> = ({ children }) => {
  const [state, setState] = useState<CanvasState>({
    messages: [],
    artifact: undefined,
    highlightedCode: undefined,
    highlightedText: undefined,
    webSearchResults: undefined,
    isEditing: false,
    chatStarted: false,
  });

  const setArtifact = (artifact: ArtifactV3) => {
    setState(prev => ({ ...prev, artifact }));
  };

  const addMessage = (content: string, role: "user" | "assistant", artifact?: ArtifactV3) => {
    const newMessage: CanvasMessage = {
      id: uuidv4(),
      content,
      role,
      timestamp: new Date(),
      artifact,
    };

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
      artifact: artifact || prev.artifact,
    }));
  };

  const setHighlightedCode = (highlight?: CodeHighlight) => {
    setState(prev => ({ ...prev, highlightedCode: highlight }));
  };

  const setHighlightedText = (highlight?: TextHighlight) => {
    setState(prev => ({ ...prev, highlightedText: highlight }));
  };

  const setWebSearchResults = (results?: SearchResult[]) => {
    setState(prev => ({ ...prev, webSearchResults: results }));
  };

  const setIsEditing = (editing: boolean) => {
    setState(prev => ({ ...prev, isEditing: editing }));
  };

  const setChatStarted = (started: boolean) => {
    setState(prev => ({ ...prev, chatStarted: started }));
  };

  const clearCanvas = () => {
    setState({
      messages: [],
      artifact: undefined,
      highlightedCode: undefined,
      highlightedText: undefined,
      webSearchResults: undefined,
      isEditing: false,
      chatStarted: false,
    });
  };

  const contextValue: CanvasContextType = {
    state,
    setArtifact,
    addMessage,
    setHighlightedCode,
    setHighlightedText,
    setWebSearchResults,
    setIsEditing,
    setChatStarted,
    clearCanvas,
  };

  return (
    <CanvasContext.Provider value={contextValue}>
      {children}
    </CanvasContext.Provider>
  );
};
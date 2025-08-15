"use client";

import React, { useState } from "react";
import { useCanvasContext } from "@/contexts/canvas-context";
import { ArtifactRenderer } from "./artifact-renderer";
import { CanvasChatInterface } from "./canvas-chat-interface";
import { QuickStartPanel } from "./quick-start-panel";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";

export const Canvas: React.FC = () => {
  const { state, setIsEditing } = useCanvasContext();
  const { chatStarted, isEditing } = state;
  const [chatCollapsed, setChatCollapsed] = useState(false);

  return (
    <div className="h-screen w-full">
      <ResizablePanelGroup direction="horizontal" className="h-full">
        {/* Chat Panel */}
        {!chatCollapsed && (
          <ResizablePanel
            defaultSize={chatStarted ? 30 : 100}
            minSize={20}
            maxSize={50}
            className="bg-gray-50"
          >
            {chatStarted ? (
              <CanvasChatInterface
                chatCollapsed={chatCollapsed}
                setChatCollapsed={setChatCollapsed}
              />
            ) : (
              <QuickStartPanel />
            )}
          </ResizablePanel>
        )}

        {/* Resizable Handle */}
        {!chatCollapsed && chatStarted && <ResizableHandle />}

        {/* Canvas Panel */}
        {chatStarted && (
          <ResizablePanel
            defaultSize={chatCollapsed ? 100 : 70}
            minSize={50}
            className="bg-white"
          >
            <ArtifactRenderer
              chatCollapsed={chatCollapsed}
              setChatCollapsed={setChatCollapsed}
              setIsEditing={setIsEditing}
              isEditing={isEditing}
            />
          </ResizablePanel>
        )}
      </ResizablePanelGroup>
    </div>
  );
};
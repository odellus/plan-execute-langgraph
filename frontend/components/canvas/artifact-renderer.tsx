"use client";

import React, { useState } from "react";
import { useCanvasContext } from "@/contexts/canvas-context";
import { ArtifactCodeV3, ArtifactMarkdownV3 } from "@/types";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Edit, Play, Copy, Download, ChevronLeft, ChevronRight } from "lucide-react";
import CodeMirror from "@uiw/react-codemirror";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import ReactMarkdown from "react-markdown";

interface ArtifactRendererProps {
  chatCollapsed: boolean;
  setChatCollapsed: (collapsed: boolean) => void;
  setIsEditing: (editing: boolean) => void;
  isEditing: boolean;
}

const getLanguageExtension = (language: string) => {
  switch (language) {
    case "javascript":
    case "typescript":
      return javascript({ typescript: language === "typescript" });
    case "python":
      return python();
    case "html":
      return html();
    case "css":
      return css();
    default:
      return javascript();
  }
};

export const ArtifactRenderer: React.FC<ArtifactRendererProps> = ({
  chatCollapsed,
  setChatCollapsed,
  setIsEditing,
  isEditing,
}) => {
  const { state, setArtifact } = useCanvasContext();
  const { artifact } = state;
  const [editedContent, setEditedContent] = useState<string>("");

  if (!artifact || artifact.contents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">No artifact selected</h3>
          <p className="text-gray-500">Start a conversation to create content</p>
        </div>
      </div>
    );
  }

  const currentContent = artifact.contents[artifact.currentIndex - 1];
  const isCodeArtifact = currentContent.type === "code";
  const isTextArtifact = currentContent.type === "text";

  const handleEdit = () => {
    if (isCodeArtifact) {
      setEditedContent((currentContent as ArtifactCodeV3).code);
    } else if (isTextArtifact) {
      setEditedContent((currentContent as ArtifactMarkdownV3).fullMarkdown);
    }
    setIsEditing(true);
  };

  const handleSave = () => {
    if (!artifact) return;

    const updatedContents = artifact.contents.map((content, index) => {
      if (index === artifact.currentIndex - 1) {
        if (isCodeArtifact) {
          return { ...content, code: editedContent } as ArtifactCodeV3;
        } else if (isTextArtifact) {
          return { ...content, fullMarkdown: editedContent } as ArtifactMarkdownV3;
        }
      }
      return content;
    });

    setArtifact({
      ...artifact,
      contents: updatedContents,
    });
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContent("");
  };

  const handleCopy = async () => {
    const content = isCodeArtifact 
      ? (currentContent as ArtifactCodeV3).code 
      : (currentContent as ArtifactMarkdownV3).fullMarkdown;
    
    try {
      await navigator.clipboard.writeText(content);
    } catch (error) {
      console.error("Failed to copy content:", error);
    }
  };

  const handleDownload = () => {
    const content = isCodeArtifact 
      ? (currentContent as ArtifactCodeV3).code 
      : (currentContent as ArtifactMarkdownV3).fullMarkdown;
    
    const extension = isCodeArtifact 
      ? getFileExtension((currentContent as ArtifactCodeV3).language)
      : "md";
    
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentContent.title}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getFileExtension = (language: string): string => {
    const extensions: Record<string, string> = {
      javascript: "js",
      typescript: "ts",
      python: "py",
      java: "java",
      c: "c",
      cpp: "cpp",
      csharp: "cs",
      php: "php",
      ruby: "rb",
      go: "go",
      rust: "rs",
      swift: "swift",
      kotlin: "kt",
      scala: "scala",
      html: "html",
      css: "css",
      sql: "sql",
      json: "json",
      xml: "xml",
      yaml: "yaml",
      markdown: "md",
    };
    return extensions[language] || "txt";
  };

  const navigateContent = (direction: "prev" | "next") => {
    if (!artifact) return;
    
    let newIndex;
    if (direction === "prev" && artifact.currentIndex > 1) {
      newIndex = artifact.currentIndex - 1;
    } else if (direction === "next" && artifact.currentIndex < artifact.contents.length) {
      newIndex = artifact.currentIndex + 1;
    } else {
      return;
    }

    setArtifact({
      ...artifact,
      currentIndex: newIndex,
    });
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gray-50">
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setChatCollapsed(!chatCollapsed)}
          >
            {chatCollapsed ? "Show Chat" : "Hide Chat"}
          </Button>
          <Separator orientation="vertical" className="h-4" />
          <h2 className="font-medium">{currentContent.title}</h2>
          <span className="text-sm text-gray-500 capitalize">
            {currentContent.type}
            {isCodeArtifact && ` • ${(currentContent as ArtifactCodeV3).language}`}
          </span>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Navigation */}
          {artifact.contents.length > 1 && (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigateContent("prev")}
                disabled={artifact.currentIndex <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-gray-500">
                {artifact.currentIndex} / {artifact.contents.length}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigateContent("next")}
                disabled={artifact.currentIndex >= artifact.contents.length}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Separator orientation="vertical" className="h-4" />
            </>
          )}
          
          {/* Actions */}
          {isEditing ? (
            <>
              <Button size="sm" onClick={handleSave}>
                Save
              </Button>
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={handleEdit}>
                <Edit className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={handleCopy}>
                <Copy className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={handleDownload}>
                <Download className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isEditing ? (
          <div className="h-full">
            {isCodeArtifact ? (
              <CodeMirror
                value={editedContent}
                onChange={(value) => setEditedContent(value)}
                extensions={[getLanguageExtension((currentContent as ArtifactCodeV3).language)]}
                theme="light"
                className="h-full"
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: true,
                  dropCursor: false,
                  allowMultipleSelections: false,
                }}
              />
            ) : (
              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="w-full h-full p-4 border-none outline-none resize-none font-mono text-sm"
                placeholder="Enter your markdown content..."
              />
            )}
          </div>
        ) : (
          <div className="h-full">
            {isCodeArtifact ? (
              <CodeMirror
                value={(currentContent as ArtifactCodeV3).code}
                extensions={[getLanguageExtension((currentContent as ArtifactCodeV3).language)]}
                theme="light"
                editable={false}
                className="h-full"
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: true,
                  dropCursor: false,
                  allowMultipleSelections: false,
                }}
              />
            ) : (
              <div className="p-4 prose prose-sm max-w-none">
                <ReactMarkdown>
                  {(currentContent as ArtifactMarkdownV3).fullMarkdown}
                </ReactMarkdown>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
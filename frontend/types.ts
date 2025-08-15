// Canvas-related types for the frontend
export type ProgrammingLanguageOptions = 
  | "javascript"
  | "typescript"
  | "python"
  | "java"
  | "c"
  | "cpp"
  | "csharp"
  | "php"
  | "ruby"
  | "go"
  | "rust"
  | "swift"
  | "kotlin"
  | "scala"
  | "html"
  | "css"
  | "sql"
  | "json"
  | "xml"
  | "yaml"
  | "markdown";

export type ArtifactType = "text" | "code";

export interface ArtifactCodeV3 {
  index: number;
  type: "code";
  title: string;
  code: string;
  language: ProgrammingLanguageOptions;
}

export interface ArtifactMarkdownV3 {
  index: number;
  type: "text";
  title: string;
  fullMarkdown: string;
}

export interface ArtifactV3 {
  currentIndex: number;
  contents: (ArtifactCodeV3 | ArtifactMarkdownV3)[];
}

export interface CodeHighlight {
  startCharIndex: number;
  endCharIndex: number;
}

export interface TextHighlight {
  startCharIndex: number;
  endCharIndex: number;
  text: string;
}

export interface SearchResult {
  url: string;
  title: string;
  content: string;
}

export interface CanvasMessage {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  artifact?: ArtifactV3;
}

export interface CanvasState {
  messages: CanvasMessage[];
  artifact?: ArtifactV3;
  highlightedCode?: CodeHighlight;
  highlightedText?: TextHighlight;
  webSearchResults?: SearchResult[];
  isEditing: boolean;
  chatStarted: boolean;
}
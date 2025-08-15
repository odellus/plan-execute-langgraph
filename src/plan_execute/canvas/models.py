from typing import List, Optional, Union, Literal
from pydantic import BaseModel
from datetime import datetime

# Programming language options
ProgrammingLanguageOptions = Literal[
    "javascript", "typescript", "python", "java", "c", "cpp", "csharp",
    "php", "ruby", "go", "rust", "swift", "kotlin", "scala", "html",
    "css", "sql", "json", "xml", "yaml", "markdown"
]

# Artifact types
ArtifactType = Literal["text", "code"]

class ArtifactCodeV3(BaseModel):
    index: int
    type: Literal["code"]
    title: str
    code: str
    language: ProgrammingLanguageOptions

class ArtifactMarkdownV3(BaseModel):
    index: int
    type: Literal["text"]
    title: str
    fullMarkdown: str

class ArtifactV3(BaseModel):
    currentIndex: int
    contents: List[Union[ArtifactCodeV3, ArtifactMarkdownV3]]

class CodeHighlight(BaseModel):
    startCharIndex: int
    endCharIndex: int

class TextHighlight(BaseModel):
    startCharIndex: int
    endCharIndex: int
    text: str

class SearchResult(BaseModel):
    url: str
    title: str
    content: str

class CanvasMessage(BaseModel):
    id: str
    content: str
    role: Literal["user", "assistant"]
    timestamp: datetime
    artifact: Optional[ArtifactV3] = None

class CanvasState(BaseModel):
    messages: List[CanvasMessage] = []
    artifact: Optional[ArtifactV3] = None
    highlightedCode: Optional[CodeHighlight] = None
    highlightedText: Optional[TextHighlight] = None
    webSearchResults: Optional[List[SearchResult]] = None
    isEditing: bool = False
    chatStarted: bool = False

# Request/Response models for API
class CanvasChatRequest(BaseModel):
    message: str
    artifact: Optional[ArtifactV3] = None

class CanvasChatResponse(BaseModel):
    message: str
    artifact: Optional[ArtifactV3] = None
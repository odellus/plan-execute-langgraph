import json
import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from plan_execute.config import settings
from .models import (
    CanvasChatRequest, 
    CanvasChatResponse, 
    ArtifactV3, 
    ArtifactCodeV3, 
    ArtifactMarkdownV3,
    ProgrammingLanguageOptions
)

logger = logging.getLogger(__name__)

class CanvasService:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool
        self.checkpointer = AsyncPostgresSaver(pool)
        self.llm = ChatOpenAI(
            model="claude4_sonnet",
            temperature=0.7,
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value()
        )

    async def initialize(self):
        """Initialize the service and set up database tables if needed."""
        await self.checkpointer.setup()

    def _get_language_template(self, language: ProgrammingLanguageOptions) -> str:
        """Get a template for the specified programming language."""
        templates = {
            "javascript": '''// Welcome to JavaScript!
console.log("Hello, World!");

function greet(name) {
  return `Hello, ${name}!`;
}

greet("Canvas");''',
            "typescript": '''// Welcome to TypeScript!
interface Greeting {
  name: string;
}

function greet(greeting: Greeting): string {
  return `Hello, ${greeting.name}!`;
}

console.log(greet({ name: "Canvas" }));''',
            "python": '''# Welcome to Python!
def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("Canvas"))''',
            "html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hello Canvas</title>
</head>
<body>
    <h1>Hello, Canvas!</h1>
    <p>Welcome to your HTML document.</p>
</body>
</html>''',
            "css": '''/* Welcome to CSS! */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    color: #333;
    text-align: center;
}''',
            "markdown": '''# Hello, Canvas!

Welcome to your markdown document. You can create rich text content with ease.

## Features

- **Bold text**
- *Italic text*
- `Code snippets`
- [Links](https://example.com)

### Code Example

```javascript
console.log("Hello from markdown!");
```

> This is a blockquote with useful information.

1. First item
2. Second item
3. Third item'''
        }
        return templates.get(language, templates["javascript"])

    def _create_artifact_prompt(self, message: str, existing_artifact: Optional[ArtifactV3] = None) -> str:
        """Create a prompt for generating or modifying artifacts."""
        base_prompt = """You are an AI assistant that helps users create and edit code and text documents. 
You can create artifacts (code files or text documents) based on user requests.

When the user asks you to create or modify content, you should:
1. Determine if they want code or text content
2. Choose appropriate language/format
3. Create well-structured, commented code or well-formatted text
4. Provide a helpful response explaining what you created

User request: {message}"""

        if existing_artifact:
            current_content = existing_artifact.contents[existing_artifact.currentIndex - 1]
            base_prompt += f"""

Existing artifact:
- Type: {current_content.type}
- Title: {current_content.title}
"""
            if current_content.type == "code":
                code_content = current_content
                base_prompt += f"- Language: {code_content.language}\n- Code:\n{code_content.code}"
            else:
                text_content = current_content
                base_prompt += f"- Content:\n{text_content.fullMarkdown}"

        return base_prompt.format(message=message)

    async def _determine_artifact_type(self, message: str) -> tuple[str, Optional[str]]:
        """Determine if the user wants to create code or text, and what language/format."""
        analysis_prompt = f"""Analyze this user request and determine:
1. Do they want to create/modify CODE or TEXT content?
2. If code, what programming language? 
3. If text, it should be markdown format.

User request: "{message}"

Respond with JSON in this format:
{{"type": "code" or "text", "language": "language_name_if_code"}}

Examples:
- "Create a Python function" -> {{"type": "code", "language": "python"}}
- "Write a blog post" -> {{"type": "text", "language": null}}
- "Make a JavaScript calculator" -> {{"type": "code", "language": "javascript"}}
- "Create documentation" -> {{"type": "text", "language": null}}
"""

        try:
            response = await self.llm.ainvoke([HumanMessage(content=analysis_prompt)])
            result = json.loads(response.content.strip())
            return result.get("type", "text"), result.get("language")
        except Exception as e:
            logger.warning(f"Failed to determine artifact type: {e}")
            # Default to text if analysis fails
            return "text", None

    async def _generate_content(self, message: str, artifact_type: str, language: Optional[str] = None, existing_artifact: Optional[ArtifactV3] = None) -> tuple[str, str]:
        """Generate content based on the user's request."""
        if existing_artifact:
            # Modify existing content
            current_content = existing_artifact.contents[existing_artifact.currentIndex - 1]
            if current_content.type == "code":
                code_content = current_content
                modify_prompt = f"""Modify this {code_content.language} code based on the user's request.

Current code:
```{code_content.language}
{code_content.code}
```

User request: {message}

Provide:
1. The modified code (just the code, no markdown formatting)
2. A brief explanation of what you changed

Format your response as:
CODE:
[your code here]

EXPLANATION:
[your explanation here]
"""
                response = await self.llm.ainvoke([HumanMessage(content=modify_prompt)])
                parts = response.content.split("EXPLANATION:")
                if len(parts) == 2:
                    code_part = parts[0].replace("CODE:", "").strip()
                    explanation = parts[1].strip()
                    return code_part, explanation
                else:
                    return current_content.code, "I couldn't modify the code as requested."
            else:
                text_content = current_content
                modify_prompt = f"""Modify this markdown content based on the user's request.

Current content:
{text_content.fullMarkdown}

User request: {message}

Provide:
1. The modified markdown content
2. A brief explanation of what you changed

Format your response as:
CONTENT:
[your markdown content here]

EXPLANATION:
[your explanation here]
"""
                response = await self.llm.ainvoke([HumanMessage(content=modify_prompt)])
                parts = response.content.split("EXPLANATION:")
                if len(parts) == 2:
                    content_part = parts[0].replace("CONTENT:", "").strip()
                    explanation = parts[1].strip()
                    return content_part, explanation
                else:
                    return text_content.fullMarkdown, "I couldn't modify the content as requested."
        else:
            # Create new content
            if artifact_type == "code":
                create_prompt = f"""Create {language} code based on this request: {message}

Requirements:
- Write clean, well-commented code
- Include proper error handling where appropriate
- Use best practices for the language
- Make it functional and ready to run

Provide:
1. The code (just the code, no markdown formatting)
2. A brief explanation of what the code does

Format your response as:
CODE:
[your code here]

EXPLANATION:
[your explanation here]
"""
                response = await self.llm.ainvoke([HumanMessage(content=create_prompt)])
                parts = response.content.split("EXPLANATION:")
                if len(parts) == 2:
                    code_part = parts[0].replace("CODE:", "").strip()
                    explanation = parts[1].strip()
                    return code_part, explanation
                else:
                    # Fallback to template
                    return self._get_language_template(language), f"Created a {language} template."
            else:
                create_prompt = f"""Create markdown content based on this request: {message}

Requirements:
- Use proper markdown formatting
- Include headers, lists, and other formatting as appropriate
- Make it well-structured and readable
- Include relevant examples if applicable

Provide:
1. The markdown content
2. A brief explanation of what you created

Format your response as:
CONTENT:
[your markdown content here]

EXPLANATION:
[your explanation here]
"""
                response = await self.llm.ainvoke([HumanMessage(content=create_prompt)])
                parts = response.content.split("EXPLANATION:")
                if len(parts) == 2:
                    content_part = parts[0].replace("CONTENT:", "").strip()
                    explanation = parts[1].strip()
                    return content_part, explanation
                else:
                    return self._get_language_template("markdown"), "Created a markdown template."

    async def chat(self, request: CanvasChatRequest) -> CanvasChatResponse:
        """Process a canvas chat request and return a response with potential artifact."""
        try:
            message = request.message.strip()
            existing_artifact = request.artifact

            # Determine what type of content to create/modify
            artifact_type, language = await self._determine_artifact_type(message)

            # Generate or modify content
            content, explanation = await self._generate_content(
                message, artifact_type, language, existing_artifact
            )

            # Create or update artifact
            if existing_artifact:
                # Update existing artifact
                current_content = existing_artifact.contents[existing_artifact.currentIndex - 1]
                if current_content.type == "code":
                    updated_content = ArtifactCodeV3(
                        index=current_content.index,
                        type="code",
                        title=current_content.title,
                        code=content,
                        language=current_content.language
                    )
                else:
                    updated_content = ArtifactMarkdownV3(
                        index=current_content.index,
                        type="text",
                        title=current_content.title,
                        fullMarkdown=content
                    )

                # Replace the current content
                updated_contents = existing_artifact.contents.copy()
                updated_contents[existing_artifact.currentIndex - 1] = updated_content

                artifact = ArtifactV3(
                    currentIndex=existing_artifact.currentIndex,
                    contents=updated_contents
                )
            else:
                # Create new artifact
                if artifact_type == "code":
                    artifact_content = ArtifactCodeV3(
                        index=1,
                        type="code",
                        title=f"New {language.title() if language else 'Code'} File",
                        code=content,
                        language=language or "javascript"
                    )
                else:
                    artifact_content = ArtifactMarkdownV3(
                        index=1,
                        type="text",
                        title="New Document",
                        fullMarkdown=content
                    )

                artifact = ArtifactV3(
                    currentIndex=1,
                    contents=[artifact_content]
                )

            return CanvasChatResponse(
                message=explanation,
                artifact=artifact
            )

        except Exception as e:
            logger.exception("Error in canvas chat")
            return CanvasChatResponse(
                message=f"I encountered an error: {str(e)}. Please try again.",
                artifact=request.artifact
            )
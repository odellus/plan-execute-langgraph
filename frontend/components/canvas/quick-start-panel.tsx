"use client";

import React, { useState } from "react";
import { useCanvasContext } from "@/contexts/canvas-context";
import { Button } from "@/components/ui/button";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Code, FileText, Sparkles } from "lucide-react";
import { ArtifactV3, ArtifactCodeV3, ArtifactMarkdownV3, ProgrammingLanguageOptions } from "@/types";

const PROGRAMMING_LANGUAGES: { value: ProgrammingLanguageOptions; label: string }[] = [
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "python", label: "Python" },
  { value: "java", label: "Java" },
  { value: "c", label: "C" },
  { value: "cpp", label: "C++" },
  { value: "csharp", label: "C#" },
  { value: "php", label: "PHP" },
  { value: "ruby", label: "Ruby" },
  { value: "go", label: "Go" },
  { value: "rust", label: "Rust" },
  { value: "swift", label: "Swift" },
  { value: "kotlin", label: "Kotlin" },
  { value: "html", label: "HTML" },
  { value: "css", label: "CSS" },
  { value: "sql", label: "SQL" },
];

const getLanguageTemplate = (language: ProgrammingLanguageOptions): string => {
  const templates: Record<ProgrammingLanguageOptions, string> = {
    javascript: `// Welcome to JavaScript!
console.log("Hello, World!");

function greet(name) {
  return \`Hello, \${name}!\`;
}

greet("Canvas");`,
    typescript: `// Welcome to TypeScript!
interface Greeting {
  name: string;
}

function greet(greeting: Greeting): string {
  return \`Hello, \${greeting.name}!\`;
}

console.log(greet({ name: "Canvas" }));`,
    python: `# Welcome to Python!
def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(greet("Canvas"))`,
    java: `// Welcome to Java!
public class Hello {
    public static void main(String[] args) {
        System.out.println(greet("Canvas"));
    }
    
    public static String greet(String name) {
        return "Hello, " + name + "!";
    }
}`,
    c: `// Welcome to C!
#include <stdio.h>

int main() {
    printf("Hello, Canvas!\\n");
    return 0;
}`,
    cpp: `// Welcome to C++!
#include <iostream>
#include <string>

std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

int main() {
    std::cout << greet("Canvas") << std::endl;
    return 0;
}`,
    csharp: `// Welcome to C#!
using System;

class Program 
{
    static void Main() 
    {
        Console.WriteLine(Greet("Canvas"));
    }
    
    static string Greet(string name) 
    {
        return $"Hello, {name}!";
    }
}`,
    php: `<?php
// Welcome to PHP!
function greet($name) {
    return "Hello, " . $name . "!";
}

echo greet("Canvas");
?>`,
    ruby: `# Welcome to Ruby!
def greet(name)
  "Hello, #{name}!"
end

puts greet("Canvas")`,
    go: `// Welcome to Go!
package main

import "fmt"

func greet(name string) string {
    return fmt.Sprintf("Hello, %s!", name)
}

func main() {
    fmt.Println(greet("Canvas"))
}`,
    rust: `// Welcome to Rust!
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn main() {
    println!("{}", greet("Canvas"));
}`,
    swift: `// Welcome to Swift!
func greet(name: String) -> String {
    return "Hello, \\(name)!"
}

print(greet(name: "Canvas"))`,
    kotlin: `// Welcome to Kotlin!
fun greet(name: String): String {
    return "Hello, $name!"
}

fun main() {
    println(greet("Canvas"))
}`,
    scala: `// Welcome to Scala!
object Hello {
  def greet(name: String): String = s"Hello, $name!"
  
  def main(args: Array[String]): Unit = {
    println(greet("Canvas"))
  }
}`,
    html: `<!DOCTYPE html>
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
</html>`,
    css: `/* Welcome to CSS! */
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
}`,
    sql: `-- Welcome to SQL!
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (name, email) VALUES 
('Canvas User', 'user@canvas.com');

SELECT * FROM users;`,
    json: `{
  "message": "Hello, Canvas!",
  "version": "1.0.0",
  "features": [
    "Code editing",
    "Syntax highlighting",
    "Real-time collaboration"
  ],
  "config": {
    "theme": "light",
    "autoSave": true
  }
}`,
    xml: `<?xml version="1.0" encoding="UTF-8"?>
<canvas>
    <title>Hello Canvas</title>
    <description>Welcome to your XML document</description>
    <features>
        <feature>Code editing</feature>
        <feature>Syntax highlighting</feature>
        <feature>Real-time collaboration</feature>
    </features>
</canvas>`,
    yaml: `# Welcome to YAML!
title: Hello Canvas
description: Welcome to your YAML document

features:
  - Code editing
  - Syntax highlighting
  - Real-time collaboration

config:
  theme: light
  autoSave: true`,
    markdown: `# Hello, Canvas!

Welcome to your markdown document. You can create rich text content with ease.

## Features

- **Bold text**
- *Italic text*
- \`Code snippets\`
- [Links](https://example.com)

### Code Example

\`\`\`javascript
console.log("Hello from markdown!");
\`\`\`

> This is a blockquote with useful information.

1. First item
2. Second item
3. Third item`,
  };

  return templates[language] || templates.javascript;
};

export const QuickStartPanel: React.FC = () => {
  const { setArtifact, setChatStarted } = useCanvasContext();
  const [selectedLanguage, setSelectedLanguage] = useState<ProgrammingLanguageOptions>("javascript");

  const handleQuickStart = (type: "text" | "code") => {
    let artifactContent: ArtifactCodeV3 | ArtifactMarkdownV3;

    if (type === "code") {
      artifactContent = {
        index: 1,
        type: "code",
        title: `New ${PROGRAMMING_LANGUAGES.find(l => l.value === selectedLanguage)?.label || "Code"} File`,
        code: getLanguageTemplate(selectedLanguage),
        language: selectedLanguage,
      };
    } else {
      artifactContent = {
        index: 1,
        type: "text",
        title: "New Document",
        fullMarkdown: getLanguageTemplate("markdown"),
      };
    }

    const newArtifact: ArtifactV3 = {
      currentIndex: 1,
      contents: [artifactContent],
    };

    setArtifact(newArtifact);
    setChatStarted(true);
  };

  return (
    <div className="flex items-center justify-center h-full p-8">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <Sparkles className="h-12 w-12 text-blue-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to Canvas</h1>
          <p className="text-gray-600">Create and edit code or text documents with AI assistance</p>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Code className="h-5 w-5" />
                <span>Create Code</span>
              </CardTitle>
              <CardDescription>
                Start with a code template in your preferred language
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                value={selectedLanguage}
                onValueChange={(value) => setSelectedLanguage(value as ProgrammingLanguageOptions)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a language" />
                </SelectTrigger>
                <SelectContent>
                  {PROGRAMMING_LANGUAGES.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={() => handleQuickStart("code")} className="w-full">
                Create Code File
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Create Document</span>
              </CardTitle>
              <CardDescription>
                Start with a markdown document for rich text content
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={() => handleQuickStart("text")} className="w-full" variant="outline">
                Create Document
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="text-center text-sm text-gray-500">
          Or start a conversation to create content with AI assistance
        </div>
      </div>
    </div>
  );
};
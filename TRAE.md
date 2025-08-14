# TRAE.md

This is a markdown file intende for trae agent. It contains the instructions for trae-agent to follow.

# INSTRUCTIONS
Configure our assistant in frontend to work with our backend in src/plan_execute


# RULES
- We use uv
- Use uv to run python scripts like uv run script.py
- We primarily want to fix the backend to interact with our custom FastAPI streaming endpoint
- Write tests to ensure what you are doing works
- Test often
- Finish soon so I can test it out in UI


# LINKS
- Instructions for adding LocalRuntime
https://www.assistant-ui.com/docs/runtimes/custom/local

# LINK CONTENTS

```ts
"use client";

import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const MyModelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    // TODO replace with your own API
    const result = await fetch("<YOUR_API_ENDPOINT>", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // forward the messages in the chat to the API
      body: JSON.stringify({
        messages,
      }),
      // if the user hits the "cancel" button or escape keyboard key, cancel the request
      signal: abortSignal,
    });

    const data = await result.json();
    return {
      content: [
        {
          type: "text",
          text: data.text,
        },
      ],
    };
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
```


```ts
"use client";

import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const MyModelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    // TODO replace with your own API
    const result = await fetch("<YOUR_API_ENDPOINT>", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // forward the messages in the chat to the API
      body: JSON.stringify({
        messages,
      }),
      // if the user hits the "cancel" button or escape keyboard key, cancel the request
      signal: abortSignal,
    });

    const data = await result.json();
    return {
      content: [
        {
          type: "text",
          text: data.text,
        },
      ],
    };
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
```


```ts
const MyModelAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal, context }) {
    const stream = await backendApi({ messages, abortSignal, context });

    let text = "";
    for await (const part of stream) {
      text += part.choices[0]?.delta?.content || "";

      yield {
        content: [{ type: "text", text }],
      };
    }
  },
};
```
# plan-execute-langgraph

> [!NOTE]
> Just a simple re-write of [this tutorial](https://langchain-ai.lang.chat/langgraph/tutorials/plan-and-execute/plan-and-execute/) to use qwen3 and searxng instrumented with phoenix arize


## Install

```bash
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env 
# Add your own phoenix api key and endpoints
nano .env
```

## Use
To execute the graph

```bash
uv run main.py
```

## Monitor 
I assume you have arize phoenix running and have set an API key. If you haven't, [do so](https://github.com/odellus/homelab). If you don't want to commit, just try

```bash
uv run phoenix serve
```

**BEFORE** running the script with `uv run main.py` above, then navigate to [`http://localhost:6006`](http://localhost:6006) to see the fireworks when you do finally run your agent. There are no extra `uv add` steps for extra dependencies, the `uv sync` already installed phoenix server in `.venv`.
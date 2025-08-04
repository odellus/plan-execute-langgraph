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
# Start postgres on localhost:5432
docker compose up -d db

# Start the whole thing 
# *Optional
docker compose up -d --build
```

## Use
To run the server

```bash
# For development outside the container
uv run -m plan_execute.app

# OR Inside the container
docker compose up -d plan-execute --build
```

## Test
`tests/unit.py` is broken right now. Use `tests/client.py` after spinning up server in another terminal with `uv run -m plan_execute.app` or the same terminal `docker compose up -d --build`.

```bash
# after you have plan-execute service running...
source .venv/bin/activate
uv run tests/client.py
```

## Monitor 
I assume you have arize phoenix running and have set an API key. If you haven't, [do so](https://github.com/odellus/homelab). If you don't want to commit, just try

```bash
uv run phoenix serve
```

**BEFORE** running the script with `uv run main.py` above, then navigate to [`http://localhost:6006`](http://localhost:6006) to see the fireworks when you do finally run your agent. There are no extra `uv add` steps for extra dependencies, the `uv sync` already installed phoenix server in `.venv`.
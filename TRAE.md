# TRAE.md

This is a markdown file intende for trae agent. It contains the instructions for trae-agent to follow.

# INSTRUCTIONS
- Create a new agent with a very simple graph that streams back the response
- Show how to set up this endpoint in fastapi
- Give an example of how to access this with a simple frontend
- use assistant-ui react typescript for simple frontend perplexity clone
- Use uv for the backend, which is currently here

thomas.wood@M3-PRO-TWood plan-execute-langgraph % tree .           
.
├── compose.yaml
├── Dockerfile
├── init-db
│   └── init-db.sql
├── pyproject.toml
├── README.md
├── src
│   └── plan_execute
│       ├── __init__.py
│       ├── agent
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── nodes.py
│       │   └── service.py
│       ├── app.py
│       └── config.py
├── tests
│   ├── client.py
│   └── unit.py
├── TRAE.md
└── uv.lock

6 directories, 16 files

# RULES
- Be prompt about it
- Think carefully and do it right
- Test frequently as you develop on the existing framework
- you run scripts with `uv run {script_name}.py`
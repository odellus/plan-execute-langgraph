FROM python:3.12-slim

WORKDIR /app

# Install `uv`
RUN --mount=type=cache,target=/root/.cache \
    pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install app dependencies
RUN --mount=type=cache,target=/root/.cache \
    uv sync --frozen

# Copy source code
COPY src ./src
# Copy any .env file for runtime overrides if desired
COPY .env ./.env

# Default command
CMD ["uv", "run", "-m", "plan_execute.app"]

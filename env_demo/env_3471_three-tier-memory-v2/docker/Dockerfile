FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

ENV UV_NO_DEV=1
RUN uv sync --no-install-project

COPY tools/ ./tools/
COPY mcp_server.py ./

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV WORKSPACE_DIR=/app/workspace

EXPOSE 8000

CMD ["sh", "-c", "python mcp_server.py & wait"]
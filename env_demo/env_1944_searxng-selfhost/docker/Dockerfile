FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

ENV UV_NO_DEV=1
RUN uv sync --no-install-project

COPY tools/ ./tools/
COPY mocks/ ./mocks/
COPY mcp_server.py test_tools.py ./

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV SEARXNG_URL=http://localhost:8888

EXPOSE 8000 8888

CMD ["sh", "-c", "\
    uvicorn mocks.searxng_api:app --host 0.0.0.0 --port 8888 & \
    python mcp_server.py & \
    wait"]
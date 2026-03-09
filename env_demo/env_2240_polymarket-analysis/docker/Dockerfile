FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

ENV UV_NO_DEV=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_INDEX_STRATEGY=unsafe-first-match
RUN uv sync --no-install-project

COPY tools/ ./tools/
COPY mocks/ ./mocks/
COPY mcp_server.py ./

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV GAMMA_API_BASE=http://localhost:8001
ENV DATA_API_BASE=http://localhost:8002

EXPOSE 8000 8001 8002

CMD ["sh", "-c", "\
    uvicorn mocks.gamma_api:app --host 0.0.0.0 --port 8001 & \
    uvicorn mocks.data_api:app --host 0.0.0.0 --port 8002 & \
    python mcp_server.py & \
    wait"]
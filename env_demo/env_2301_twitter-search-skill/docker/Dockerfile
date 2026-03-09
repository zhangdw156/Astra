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
COPY mcp_server.py test_tools.py ./

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV TWITTER_API_BASE=http://localhost:8003
ENV TWITTER_API_KEY=mock-api-key

EXPOSE 8000 8003

CMD ["sh", "-c", "\
    uvicorn mocks.twitter_api:app --host 0.0.0.0 --port 8003 & \
    python mcp_server.py & \
    wait"]
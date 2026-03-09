# 使用 uv 官方镜像（Python 3.13 + uv 预装）
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
ENV TWITTER_API_BASE=http://localhost:8003
ENV FARCASTER_API_BASE=http://localhost:8004
ENV X_CONSUMER_KEY=mock-consumer-key
ENV X_CONSUMER_SECRET=mock-consumer-secret
ENV X_ACCESS_TOKEN=mock-access-token
ENV X_ACCESS_TOKEN_SECRET=mock-access-secret
ENV FARCASTER_API_KEY=mock-api-key

EXPOSE 8000 8003 8004

CMD ["sh", "-c", "\
    uvicorn mocks.twitter_api:app --host 0.0.0.0 --port 8003 & \
    uvicorn mocks.farcaster_api:app --host 0.0.0.0 --port 8004 & \
    python mcp_server.py & \
    wait"]
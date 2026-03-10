# 使用 uv 官方镜像（Python 3.13 + uv 预装）
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

# 安装 curl（健康检查需要）
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖配置，利用层缓存
COPY pyproject.toml ./

# 安装依赖（无 lock 时 uv 会解析 pyproject.toml）
ENV UV_NO_DEV=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_INDEX_STRATEGY=unsafe-first-match
RUN uv sync --no-install-project

# 复制业务代码（路径相对于 build context，即项目根）
COPY tools/ ./tools/
COPY mocks/ ./mocks/
COPY database/ ./database/
COPY state.py mcp_server.py test_tools.py ./

# 状态库路径：容器内统一使用 /app/data/state.db，可挂载卷实现持久化
ENV STATE_DB_PATH=/app/data/state.db
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV UNIFAI_API_BASE=http://localhost:8001
ENV KALSHI_API_BASE=http://localhost:8002
ENV UNIFAI_AGENT_API_KEY=mock-api-key

# 暴露端口
# 8000: MCP Server | 8001: UnifAI Mock API | 8002: Kalshi Mock API
EXPOSE 8000 8001 8002

# 启动：先初始化 SQLite Schema 与初始数据，再启动 MCP + Mock 服务
CMD ["sh", "-c", "\
    python -c \"from state import ensure_schema_and_initial_data; ensure_schema_and_initial_data()\" && \
    uvicorn mocks.unifai_api:app --host 0.0.0.0 --port 8001 & \
    uvicorn mocks.kalshi_api:app --host 0.0.0.0 --port 8002 & \
    python mcp_server.py & \
    wait"]

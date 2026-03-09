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
RUN uv sync --no-install-project

# 复制业务代码
COPY tools/ ./tools/
COPY mocks/ ./mocks/
COPY mcp_server.py test_tools.py ./
COPY config.json ./config.json

# 设置环境变量
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV POLYMARKET_API_BASE=http://localhost:8001

# 暴露端口
# 8000: MCP Server
# 8001: Polymarket Mock API
EXPOSE 8000 8001

# 启动命令：后台启动所有服务，wait 保持主进程不退出
CMD ["sh", "-c", "\
    uvicorn mocks.polymarket_api:app --host 0.0.0.0 --port 8001 & \
    python mcp_server.py & \
    wait"]
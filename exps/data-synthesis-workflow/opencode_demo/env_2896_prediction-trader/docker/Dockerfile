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
# 轻量环境仅依赖 mcp_server.py、llm_response.py 与 tools.jsonl
COPY mcp_server.py llm_response.py tools.jsonl ./

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV ENV_MODE=light

# 仅暴露 MCP Server 端口
EXPOSE 8000

# 启动：直接运行轻量 MCP 服务（tools.jsonl + KV state）
CMD ["python", "mcp_server.py"]

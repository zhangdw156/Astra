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

# 复制业务代码（路径相对于 build context，即项目根）
COPY tools/ ./tools/
COPY mcp_server.py tools.jsonl ./

# 设置环境变量
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http

# 暴露端口
# 8000: MCP Server
EXPOSE 8000

# 启动命令：后台启动 MCP 服务，wait 保持主进程不退出
# 注意：此环境依赖浏览器工具进行实际的 LinkedIn 操作
# 工具返回浏览器自动化指令，需要代理/agent 执行这些指令
CMD ["sh", "-c", "\
    python mcp_server.py & \
    wait"]
# 使用 uv 官方镜像（Python 3.13 + uv 预装）
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /work

# 仅安装基础工具；业务代码与配置通过挂载提供
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV UV_NO_DEV=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_INDEX_STRATEGY=unsafe-first-match

ENV PYTHONPATH=/work
ENV WORK_DIR=/work
ENV PATH="/work/.venv/bin:$PATH"

EXPOSE 8000

# 构建时拷贝依赖定义与 tools.jsonl；运行时挂载 .env、prompts、app
COPY pyproject.toml tools.jsonl ./
RUN uv sync --no-install-project

CMD ["sh", "-c", "MCP_TRANSPORT=sse uv run python -m app.mcp_server"]

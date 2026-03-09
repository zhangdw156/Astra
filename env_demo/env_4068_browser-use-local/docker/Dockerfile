# Use uv official image (Python 3.13 + uv pre-installed)
FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim

WORKDIR /app

# Install system dependencies for browser automation
# chromium, fonts, and other dependencies needed for browser-use
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    # Chromium dependencies
    chromium \
    chromium-sandbox \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    # Fonts for rendering
    fonts-liberation \
    fonts-noto-cjk \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install browser-use Python package
RUN uv pip install --system browser-use playwright && \
    playwright install chromium --with-deps

# Copy dependency configuration first for layer caching
COPY pyproject.toml ./

# Install Python dependencies
ENV UV_NO_DEV=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV UV_INDEX_STRATEGY=unsafe-first-match
RUN uv sync --no-install-project

# Copy business code
COPY tools/ ./tools/
COPY mcp_server.py test_tools.py ./

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"
ENV MCP_TRANSPORT=http
ENV BROWSER_USE_CLI=browser-use

# Environment variables for LLM (configure for your provider)
ENV OPENAI_API_KEY=${OPENAI_API_KEY:-}
ENV OPENAI_BASE_URL=${OPENAI_BASE_URL:-https://api.moonshot.cn/v1}

# Expose MCP port
# 8000: MCP Server
EXPOSE 8000

# Health check - verify basic Python functionality
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python3 -c "import browser_use; print('browser-use OK')" || exit 1

# Start command
CMD ["sh", "-c", "python mcp_server.py & wait"]
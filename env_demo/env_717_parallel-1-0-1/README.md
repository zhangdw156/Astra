# Parallel.ai Search Environment

High-accuracy web search via Parallel.ai API for AI agents.

## Directory Layout

```
env_717_parallel-1-0-1/
├── SKILL.md              # Source skill definition
├── pyproject.toml        # Python dependencies
├── mcp_server.py         # MCP server with dynamic tool discovery
├── tools.jsonl           # Tool schemas
├── test_tools.py         # Smoke tests
│
├── tools/                # MCP tool implementations
│   ├── __init__.py
│   └── search.py         # Parallel.ai search tool
│
├── mocks/                # Mock APIs
│   └── parallel_api.py   # Parallel.ai API mock
│
└── docker/               # Docker configuration
    ├── Dockerfile
    └── docker-compose.yaml
```

## Tools

| Tool | Description |
|------|-------------|
| `search` | High-accuracy web search via Parallel.ai API |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `PARALLEL_API_BASE` | `http://localhost:8001` | Parallel.ai API base URL |
| `PARALLEL_API_KEY` | `mock-api-key` | API key for authentication |

## Running Locally

```bash
# Install dependencies
uv sync

# Start Mock API
uvicorn mocks.parallel_api:app --port 8001 &

# Start MCP server (stdio mode)
python mcp_server.py

# Or with HTTP transport
MCP_TRANSPORT=http python mcp_server.py
```

## Running with Docker

```bash
# Build
docker compose -f docker/docker-compose.yaml build

# Start
docker compose -f docker/docker-compose.yaml up -d

# Logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

## Ports

- `8000`: MCP Server (HTTP mode)
- `8001`: Parallel.ai Mock API

## Usage

```python
from tools.search import execute

result = execute(
    objective="Who is the CEO of Anthropic?",
    max_results=5,
    mode="one-shot"
)
print(result)
```
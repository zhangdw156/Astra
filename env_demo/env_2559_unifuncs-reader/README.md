# UniFuncs Reader MCP Environment

MCP environment for reading web pages, PDF, Word documents using UniFuncs API with AI content extraction.

## Directory Layout

```
env_2559_unifuncs-reader/
├── SKILL.md                 # Source skill definition
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server entry point with dynamic tool discovery
├── tools.jsonl              # Tool schemas in JSONL format
├── test_tools.py            # Optional: tool smoke tests
│
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   └── read.py              # UniFuncs read tool
│
├── docker/
│   ├── Dockerfile           # Container build with uv
│   └── docker-compose.yaml  # Service composition
│
├── mocks/                   # Mock APIs
│   └── unifuncs_api.py      # UniFuncs API mock
│
└── README.md                # This file
```

## Tools

### read

Read web pages, PDF, Word documents using UniFuncs API with AI content extraction.

**Parameters:**
- `url` (required): URL to read
- `format`: Output format (markdown, md, text, txt)
- `lite_mode`: Enable lite mode for readable content only
- `include_images`: Include images in output
- `only_css_selectors`: CSS selectors to include
- `exclude_css_selectors`: CSS selectors to exclude
- `link_summary`: Append all page links to content
- `ignore_cache`: Re-fetch ignoring cache
- `topic`: Extract specific topic using AI
- `preserve_source`: Add source reference per paragraph
- `temperature`: LLM randomness (0.0-1.5)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | stdio | Transport mode: stdio, http, sse |
| `UNIFUNCS_API_BASE` | http://localhost:8001 | UniFuncs API base URL |
| `UNIFUNCS_API_KEY` | mock-api-key | API key for authentication |

## Running Locally

### With Docker

```bash
# Build
docker compose -f docker/docker-compose.yaml build

# Start
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

### Local Development

```bash
# Install dependencies
uv sync

# Start mock API
uvicorn mocks.unifuncs_api:app --port 8001

# Start MCP server (in another terminal)
MCP_TRANSPORT=http python mcp_server.py
```

## Ports

- **8000**: MCP Server (HTTP/SSE transport)
- **8001**: UniFuncs Mock API

## Mock Mode

In mock mode, a placeholder API key is sufficient. The mock returns preset content for common domains (example.com, github.com) and generic content for others.

To use real APIs, set the appropriate environment variables with actual API keys:
- `UNIFUNCS_API_KEY`: Your UniFuncs API key from https://unifuncs.com/account
- `UNIFUNCS_API_BASE`: Real API endpoint (default: https://api.unifuncs.com)
# SearXNG Self-Hosted Search MCP Environment

Based on the searxng skill - self-hosted web search aggregator for agents.

## Directory Structure

```
searxng-selfhost/
├── SKILL.md                    # Original skill definition
├── docker/                     # Docker configuration
│   ├── Dockerfile              # Container image build
│   └── docker-compose.yaml    # Service orchestration
├── pyproject.toml              # Python dependencies (uv managed)
├── mcp_server.py               # MCP service entry point
├── test_tools.py               # Tool testing script
├── tools.jsonl                 # Tool schema definitions
│
├── tools/                      # MCP tool implementations
│   ├── __init__.py
│   └── search.py              # Web search tool
│
└── mocks/                      # Mock API services
    └── searxng_api.py         # SearXNG Mock API
```

## Quick Start

### 1. Start Services

```bash
cd searxng-selfhost

# Build and start all services
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop services
docker compose -f docker/docker-compose.yaml down
```

### 2. Test Tools

```bash
# Enter container
docker compose -f docker/docker-compose.yaml exec searxng-selfhost bash

# Run tests
python test_tools.py
```

### 3. Use MCP Service

MCP service runs at `http://localhost:8000`, supports stdio and SSE modes.

## Available Tools

| Tool | Description |
|------|-------------|
| `search` | Search the web using SearXNG with fallback to Wikipedia + GitHub |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_URL` | http://localhost:8888 | SearXNG instance URL |
| `MCP_TRANSPORT` | stdio | MCP transport mode (stdio/http) |

## Ports

| Port | Service |
|------|---------|
| 8000 | MCP Server |
| 8888 | SearXNG Mock API |

## Data Synthesis Workflow

### Step 1: Define Scenarios

```json
{
  "session_id": "session_001",
  "skill": "searxng-selfhost",
  "scenarios": [
    {
      "turn": 1,
      "user": "Search for python tutorial",
      "expected_tool": "search",
      "expected_params": {"query": "python tutorial"}
    }
  ]
}
```

### Step 2: Call Tools

LLM selects tools based on user input:

```
User: Search for python tutorial
Assistant: Let me search for that.
[Calls: search(query="python tutorial")]
```

### Step 3: Collect Trajectories

```json
{
  "session_id": "session_001",
  "turns": [
    {
      "role": "user",
      "content": "Search for python tutorial"
    },
    {
      "role": "assistant",
      "content": "Let me search for that.",
      "tool_calls": [
        {
          "name": "search",
          "arguments": {"query": "python tutorial"}
        }
      ]
    },
    {
      "role": "tool",
      "name": "search",
      "content": "## Search Results: python tutorial\n\n..."
    }
  ]
}
```

## Notes

- All tool calls return mock data for training
- No API keys required
- Falls back to Wikipedia + GitHub when SearXNG is unavailable
- Mock data is static, suitable for "tool selection" training
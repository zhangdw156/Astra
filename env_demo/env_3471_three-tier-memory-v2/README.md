# Three-Tier Memory Management MCP Server

Three-tier memory management system for AI agents: short-term (sliding window), medium-term (summaries), and long-term (vector store with ChromaDB).

## Directory Layout

```
env_3471_three-tier-memory-v2/
├── mcp_server.py           # MCP server entry with dynamic tool discovery
├── tools.jsonl             # Tool schema definitions
├── pyproject.toml          # Python dependencies
├── tools/                  # MCP tool implementations
│   ├── init_memory_system.py
│   ├── add_short_term_memory.py
│   ├── add_medium_term_memory.py
│   ├── add_long_term_memory.py
│   ├── search_long_term_memory.py
│   ├── trigger_summary.py
│   ├── show_status.py
│   └── show_window.py
└── docker/
    ├── Dockerfile
    └── docker-compose.yaml
```

## Tools

| Tool | Description |
|------|-------------|
| `init_memory_system` | Initialize the three-tier memory system |
| `add_short_term_memory` | Add a short-term memory (sliding window) |
| `add_medium_term_memory` | Add a medium-term memory (summary) |
| `add_long_term_memory` | Add a long-term memory (ChromaDB vector store) |
| `search_long_term_memory` | Search long-term memory using vector similarity |
| `trigger_summary` | Manually trigger summary generation |
| `show_status` | Show current status of all memory tiers |
| `show_window` | Show current short-term memory window |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | stdio | Transport mode: `stdio` or `http` |
| `WORKSPACE_DIR` | `/tmp/memory-workspace` | Directory for memory storage |

## Running Locally

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode)
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

## Docker Ports

- `8000`: MCP Server

## Architecture

| Tier | Storage | Trigger | Purpose |
|------|---------|---------|---------|
| Short-term | `memory/sliding-window.json` | Real-time | Keep current conversation coherent |
| Medium-term | `memory/summaries/` | Token threshold | Compress history, retain main points |
| Long-term | `memory/vector-store/` | Semantic search | Permanent memory, RAG |
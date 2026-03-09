# Kubera MCP Environment

MCP environment for Kubera portfolio data query and management.

## Overview

This environment provides MCP tools for interacting with Kubera.com portfolio data, including:
- Listing portfolios
- Getting net worth summaries with asset allocation
- Listing and searching assets
- Updating asset values

## Directory Layout

```
env_2331_kubera-skill/
├── SKILL.md                 # Original skill definition
├── pyproject.toml           # Python dependencies (uv-compatible)
├── mcp_server.py            # MCP server entry with dynamic tool discovery
├── tools.jsonl              # Tool schemas (one JSON per line)
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── list_portfolios.py   # List all portfolios
│   ├── get_summary.py       # Net worth summary with allocation
│   ├── get_portfolio_json.py # Full portfolio JSON
│   ├── list_assets.py       # List assets with filtering/sorting
│   ├── search_assets.py     # Search assets by name/ticker
│   └── update_asset.py      # Update asset values
├── docker/
│   ├── Dockerfile           # Container build with uv
│   └── docker-compose.yaml  # Service orchestration
├── mocks/
│   └── kubera_api.py        # Mock Kubera API for testing
└── README.md                # This file
```

## Tools

| Tool | Description |
|------|-------------|
| `list_portfolios` | List all portfolios in the Kubera account |
| `get_summary` | Get net worth summary with asset allocation and top holdings |
| `get_portfolio_json` | Get full portfolio data as raw JSON |
| `list_assets` | List assets with optional sheet filtering and sorting |
| `search_assets` | Search assets by name, ticker, or account |
| `update_asset` | Update asset values (requires confirm=true) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KUBERA_API_BASE` | Kubera API base URL | `http://localhost:8003` |
| `KUBERA_API_KEY` | Kubera API key | `mock-api-key` |
| `KUBERA_SECRET` | Kubera API secret | `mock-secret` |
| `MCP_TRANSPORT` | MCP transport mode (http/sse/stdio) | `stdio` |

## Running with Docker

```bash
# Build the image
docker compose -f docker/docker-compose.yaml build

# Start services
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop services
docker compose -f docker/docker-compose.yaml down
```

## Running Locally (without Docker)

```bash
# Install dependencies with uv
uv sync

# Start Mock API (in one terminal)
uvicorn mocks.kubera_api:app --port 8003

# Start MCP server (in another terminal)
MCP_TRANSPORT=http python mcp_server.py
```

## Ports

- **8000**: MCP Server (SSE transport)
- **8003**: Kubera Mock API

## Mock Data

The mock API includes sample portfolios with:
- Crypto assets (Bitcoin, Ethereum)
- Equities (Apple, Google, Tesla, Shopify)
- Real Estate (Primary Residence)
- Cash (Checking account)
- Retirement accounts (401k, Roth IRA)
- Debts (Mortgage, Auto loan)

## Testing Tools

```bash
# Test list_portfolios
python -c "from tools.list_portfolios import execute; print(execute())"

# Test get_summary
python -c "from tools.get_summary import execute; print(execute())"

# Test search_assets
python -c "from tools.search_assets import execute; print(execute('bitcoin'))"
```

## Notes

- Mock API uses HMAC-SHA256 authentication (same as real API)
- Set `confirm=true` in update_asset to actually execute updates
- For production use, set real `KUBERA_API_KEY` and `KUBERA_SECRET` environment variables
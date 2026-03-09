# Polymarket Whale Copier

MCP environment for copying winning Polymarket wallets.

## Overview

This environment provides MCP tools for:
- Getting wallet transaction history
- Getting wallet positions
- Getting trending markets
- Getting market details
- Listing known whale wallets
- Simulating copy trades
- Getting copy trading settings

## Directory Layout

```
env_2901_polymarket-whale-copier/
├── SKILL.md                    # Skill definition (copied from input)
├── pyproject.toml              # Python dependencies
├── mcp_server.py               # MCP server entry point
├── tools.jsonl                 # Tool definitions (JSONL format)
├── test_tools.py               # Tool smoke tests
├── config.json                 # Default copy trading config
│
├── tools/                      # MCP tool implementations
│   ├── __init__.py
│   ├── get_wallet_transactions.py
│   ├── get_wallet_positions.py
│   ├── get_trending_markets.py
│   ├── get_market_details.py
│   ├── list_known_whales.py
│   ├── simulate_copy_trade.py
│   └── get_copy_settings.py
│
├── mocks/                      # Mock APIs for testing
│   └── polymarket_api.py       # Polymarket API mock
│
└── docker/                     # Docker configuration
    ├── Dockerfile
    └── docker-compose.yaml
```

## Available Tools

| Tool | Description |
|------|-------------|
| `get_wallet_transactions` | Get transaction history for a Polymarket wallet |
| `get_wallet_positions` | Get current positions for a Polymarket wallet |
| `get_trending_markets` | Get trending prediction markets from Polymarket |
| `get_market_details` | Get detailed information for a specific market |
| `list_known_whales` | List known whale wallets from leaderboard |
| `simulate_copy_trade` | Simulate copying a whale's trade |
| `get_copy_settings` | Get current copy trading configuration |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POLYMARKET_API_BASE` | `http://localhost:8001` | Polymarket API base URL |
| `MCP_TRANSPORT` | `stdio` | MCP transport mode (`stdio` or `http`) |
| `CONFIG_PATH` | `/app/config.json` | Path to copy trading config |

## Running Locally

### Using Docker

```bash
# Build and start
cd docker
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

### Running MCP Server

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode)
python mcp_server.py

# Run MCP server (HTTP/SSE mode)
MCP_TRANSPORT=http python mcp_server.py
```

### Running Mocks

```bash
# Start Polymarket mock API
uvicorn mocks.polymarket_api:app --host 0.0.0.0 --port 8001
```

## Ports

- **8000**: MCP Server (when using HTTP transport)
- **8001**: Polymarket Mock API

## Mock Data

The mock API includes:
- 3 known whale wallets
- 5 prediction markets
- Sample transactions and positions
- Leaderboard data

## Testing

Run smoke tests:
```bash
python test_tools.py
```

Note: Tests require the mock API to be running on port 8001.
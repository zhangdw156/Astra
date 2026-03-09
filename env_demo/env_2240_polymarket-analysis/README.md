# Polymarket Analysis MCP Environment

Analysis and opportunity identification for Polymarket prediction markets.

## Overview

This MCP environment provides tools for analyzing Polymarket prediction markets, including:
- Market analysis
- Monitoring for alerts
- User profile tracking
- Arbitrage detection
- Whale tracking
- Sentiment analysis

## Directory Structure

```
env_2240_polymarket-analysis/
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server entry point
├── tools.jsonl              # Tool schemas (JSONL format)
├── tools/                   # MCP tool implementations
│   ├── analyze_market.py
│   ├── monitor_market.py
│   ├── fetch_user_profile.py
│   ├── detect_arbitrage.py
│   ├── track_whales.py
│   └── analyze_sentiment.py
├── mocks/                   # Mock APIs for local development
│   ├── gamma_api.py         # Mock Gamma API (market data)
│   └── data_api.py          # Mock Data API (user data)
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yaml
└── README.md
```

## Tools

| Tool | Description |
|------|-------------|
| `analyze_market` | One-time market analysis with arbitrage and momentum signals |
| `monitor_market` | Monitor a market for price changes, whale trades, and arbitrage alerts |
| `fetch_user_profile` | Fetch user positions, trades, and P&L by wallet address |
| `detect_arbitrage` | Scan markets for pair cost arbitrage opportunities (YES + NO < $1.00) |
| `track_whales` | Track whale activity and high-volume markets |
| `analyze_sentiment` | Analyze market sentiment based on price levels |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport mode: `stdio` or `http` |
| `GAMMA_API_BASE` | `http://localhost:8001` | Gamma API base URL |
| `DATA_API_BASE` | `http://localhost:8002` | Data API base URL |

## Running with Docker

```bash
# Build the image
docker compose -f docker/docker-compose.yaml build

# Start the service
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop the service
docker compose -f docker/docker-compose.yaml down
```

## Ports

| Port | Service |
|------|---------|
| 8000 | MCP Server |
| 8001 | Gamma Mock API |
| 8002 | Data Mock API |

## Local Development

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode)
python mcp_server.py

# Run mock APIs
uvicorn mocks.gamma_api:app --port 8001
uvicorn mocks.data_api:app --port 8002
```

## Mock Data

The environment includes mock data for testing:
- 10 sample markets (Bitcoin, Fed rates, elections, etc.)
- Sample user positions for wallet `0x7845bc5e15bc9c41be5ac0725e68a16ec02b51b5`
- Sample trades and P&L history
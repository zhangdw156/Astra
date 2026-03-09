# Prediction Trader Environment

AI-powered prediction market analysis across Polymarket and Kalshi with social signals.

## Directory Layout

```
env_2896_prediction-trader/
├── SKILL.md                    # Skill definition (from input)
├── pyproject.toml              # Python dependencies
├── mcp_server.py               # MCP server entry point
├── tools.jsonl                 # Tool schemas (JSONL format)
├── test_tools.py               # Optional: smoke test for tools
│
├── tools/                      # MCP tool implementations
│   ├── __init__.py
│   ├── compare_markets.py      # Compare markets across platforms
│   ├── trending.py             # Get trending from both platforms
│   ├── analyze_topic.py        # Full topic analysis
│   ├── polymarket_trending.py  # Polymarket trending
│   ├── polymarket_crypto.py    # Polymarket crypto markets
│   ├── polymarket_search.py    # Search Polymarket
│   ├── kalshi_fed.py           # Fed rate markets
│   ├── kalshi_economics.py     # Economics markets (GDP, CPI)
│   └── kalshi_search.py        # Search Kalshi
│
├── mocks/                      # Mock APIs for testing
│   ├── __init__.py
│   ├── kalshi_api.py           # Mock Kalshi API (port 8002)
│   └── unifai_api.py           # Mock UnifAI/Polymarket API (port 8001)
│
└── docker/                     # Docker configuration
    ├── Dockerfile              # Container build
    └── docker-compose.yaml     # Service orchestration
```

## Tools

| Tool | Description |
|------|-------------|
| `compare_markets` | Compare prediction markets for a topic across both Polymarket and Kalshi |
| `trending` | Get trending markets from both platforms |
| `analyze_topic` | Full analysis of a topic including market data and consensus |
| `polymarket_trending` | Get trending events from Polymarket |
| `polymarket_crypto` | Get cryptocurrency prediction markets |
| `polymarket_search` | Search Polymarket for specific markets |
| `kalshi_fed` | Get Federal Reserve interest rate markets |
| `kalshi_economics` | Get economics markets (GDP, CPI) |
| `kalshi_search` | Search Kalshi for specific markets |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | MCP transport mode (stdio/http/sse) | stdio |
| `UNIFAI_API_BASE` | Polymarket API base URL | http://localhost:8001 |
| `KALSHI_API_BASE` | Kalshi API base URL | http://localhost:8002 |
| `UNIFAI_AGENT_API_KEY` | API key for UnifAI | mock-api-key |

## Running Locally

### Using Docker

```bash
cd docker
docker compose up -d
```

This starts:
- MCP Server on port 8000
- UnifAI Mock API on port 8001
- Kalshi Mock API on port 8002

### Running Locally (without Docker)

```bash
# Install dependencies
uv sync

# Start mock APIs
uvicorn mocks.unifai_api:app --port 8001 &
uvicorn mocks.kalshi_api:app --port 8002 &

# Start MCP server (stdio mode)
python mcp_server.py
```

## API Endpoints (Mocks)

### UnifAI Mock API (port 8001)

- `GET /health` - Health check
- `GET /v1/agent/trending` - Get trending markets
- `GET /v1/agent/crypto` - Get crypto markets
- `GET /v1/agent/search?q=<query>` - Search markets

### Kalshi Mock API (port 8002)

- `GET /health` - Health check
- `GET /markets/fed` - Fed rate markets
- `GET /markets/economics` - Economics markets
- `GET /markets/trending` - Trending markets
- `GET /markets/search?q=<query>` - Search markets

## Supported Platforms

- **Polymarket**: Offshore prediction market on Polygon (crypto, politics, sports)
- **Kalshi**: CFTC-regulated US prediction market (Fed rates, GDP, CPI, economics)

## Notes

- All prices are shown as decimals (e.g., 0.75 = 75% probability)
- This tool is read-only; trading requires platform authentication
- Polymarket data accessed via UnifAI tools
- Kalshi data accessed via direct public API (no auth for read)
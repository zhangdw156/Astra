# Polymarket Copytrading Environment

镜像成功的 Polymarket 交易员头寸的 MCP 环境。

## Directory Layout

```
env_1840_polymarket-copytrading/
├── SKILL.md                 # Skill definition
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server entry with dynamic tool discovery
├── tools.jsonl              # Tool schema definitions
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── copytrade_wallets.py
│   ├── get_wallet_positions.py
│   ├── get_my_positions.py
│   ├── get_config.py
│   ├── sell_whale_exits.py
│   └── get_portfolio.py
├── mocks/                   # Mock APIs
│   └── simmer_api.py        # Simmer API mock
├── docker/
│   ├── Dockerfile           # Container build
│   └── docker-compose.yaml  # Service orchestration
└── README.md                # This file
```

## Tools

| Tool | Description |
|------|-------------|
| `copytrade_wallets` | Run copytrading to mirror positions from specific wallets |
| `get_wallet_positions` | Get current positions of a specific wallet |
| `get_my_positions` | Get user's current copytrading positions |
| `get_config` | Get current copytrading configuration |
| `sell_whale_exits` | Sell positions when whales exit |
| `get_portfolio` | Get portfolio balance information |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | MCP transport mode (`http`/`sse` or `stdio`) | `stdio` |
| `SIMMER_API_BASE` | Simmer API base URL | `http://localhost:8001` |
| `SIMMER_API_KEY` | Simmer API key | `mock-api-key` |

## Running with Docker

```bash
# Build and start
cd docker
docker compose up -d

# Check logs
docker compose logs -f

# Stop
docker compose down
```

## Running Locally

```bash
# Install dependencies
uv sync

# Start Mock API
uvicorn mocks.simmer_api:app --port 8001 &

# Start MCP Server
python mcp_server.py
```

## MCP Connection

- **HTTP/SSE Mode**: Connect to `http://localhost:8000`
- **Stdio Mode**: Use stdio transport (for local/IDE use)

## Mock Data

The mock API includes:
- Sample whale wallet positions
- User portfolio with simulated P&L
- Copytrading execution with random trade results

For real usage, replace mock API with actual Simmer API credentials.
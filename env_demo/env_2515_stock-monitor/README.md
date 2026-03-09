# Stock Monitor MCP Environment

Real-time stock price monitoring using Yahoo Finance API with customizable price alert thresholds.

## Directory Layout

```
env_2515_stock-monitor/
├── SKILL.md                 # Original skill definition
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server entry (dynamic tool discovery)
├── tools.jsonl              # Tool schemas (for blueprint generation)
├── test_tools.py            # Smoke tests for tools
│
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── monitor_stocks.py    # Monitor all stocks for alerts
│   ├── get_stock_price.py   # Get current price for a symbol
│   ├── configure_stocks.py  # Add/update stock configuration
│   ├── get_stock_config.py  # Get current stock configuration
│   ├── get_alert_status.py  # Get alert status for stocks
│   └── reset_alerts.py      # Reset alert status
│
├── docker/
│   ├── Dockerfile           # Container build
│   └── docker-compose.yaml  # Service orchestration
│
└── mocks/
    ├── __init__.py
    └── yahoo_finance_api.py # Mock Yahoo Finance API

```

## Tools

| Tool | Description |
|------|-------------|
| `configure_stocks` | Add or update stock configuration for monitoring |
| `get_alert_status` | Get current alert status for all configured stocks |
| `get_stock_config` | Get the current list of configured stocks |
| `get_stock_price` | Get current price for a specific stock symbol |
| `monitor_stocks` | Monitor all configured stocks and check for price alerts |
| `reset_alerts` | Reset alert status for stocks |

## Alert Rules

- **First Alert**: Price change exceeds 2%
- **Follow-up Alert**: Within the same day, another 1% move from last alert price
- **Reset**: New day automatically resets base price to previous close

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | MCP transport (stdio or http/sse) |
| `STOCK_API_BASE` | `http://localhost:8003` | Yahoo Finance API base URL |

## Running

### Docker

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

### Local Development

```bash
# Install dependencies
uv sync

# Start Mock API (port 8003)
uvicorn mocks.yahoo_finance_api:app --port 8003

# Start MCP Server (port 8000)
python mcp_server.py
```

## Ports

| Port | Service |
|------|---------|
| 8000 | MCP Server |
| 8003 | Yahoo Finance Mock API |

## Stock Symbol Format

- A-shares: `600519.SS` (Kweichow Moutai)
- HK stocks: `0700.HK` (Tencent)
- US stocks: `AAPL`, `MSFT`, `GOOGL`

## Supported Stocks (Mock)

The mock API supports: 600519.SS, 0700.HK, PDD, AAPL, MSFT, GOOGL, AMZN, TSLA, BABA, TCEHY, 9988.HK, 3690.HK, 1810.HK
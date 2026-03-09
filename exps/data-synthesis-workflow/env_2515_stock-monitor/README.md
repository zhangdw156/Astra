# Stock Monitor MCP Environment

Real-time stock price monitoring using Yahoo Finance API with price alert capabilities.

## Directory Layout

```
env_2515_stock-monitor/
├── SKILL.md                 # Original skill definition
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server entry with dynamic tool discovery
├── tools.jsonl              # Tool schemas (name, description, inputSchema)
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── get_stock_price.py
│   ├── get_multiple_stock_prices.py
│   └── check_stock_alert.py
├── mocks/                   # Mock APIs
│   └── yahoo_finance_api.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yaml
└── README.md
```

## Tools

| Tool | Description |
|------|-------------|
| `get_stock_price` | Get real-time price for a single stock |
| `get_multiple_stock_prices` | Get prices for multiple stocks |
| `check_stock_alert` | Check if stock triggers alert at 2%/1% thresholds |

## Running

### Docker

```bash
cd docker
docker compose up -d
```

### Local

```bash
# Install dependencies
uv sync

# Start Mock API
uvicorn mocks.yahoo_finance_api:app --port 8003 &

# Start MCP Server
python mcp_server.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | stdio | Transport mode (stdio, http, sse) |
| `YAHOO_FINANCE_BASE` | http://localhost:8003 | Mock API base URL |
| `USE_MOCK` | true | Use mock API or real Yahoo Finance |

## Ports

- **8000**: MCP Server
- **8003**: Yahoo Finance Mock API
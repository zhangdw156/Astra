# Portfolio Risk Analyzer - MCP Environment

AI-powered crypto portfolio risk analysis with automated $BANKR buyback monetization.

## Directory Structure

```
portfolio-risk-analyzer/
├── SKILL.md                    # Original skill definition
├── docker/                     # Docker files
│   ├── Dockerfile              # Container image build
│   └── docker-compose.yaml    # Service orchestration
├── pyproject.toml              # Python dependencies (uv)
├── mcp_server.py               # MCP server entry
├── tools.jsonl                 # Tool schemas
│
├── tools/                      # MCP tool definitions
│   ├── __init__.py
│   ├── analyze_portfolio.py    # Full portfolio analysis
│   ├── get_risk_breakdown.py   # Detailed risk breakdown
│   ├── run_stress_test.py      # Stress test scenarios
│   ├── get_optimization.py     # Optimization recommendations
│   ├── verify_payment.py       # Payment/BANKR verification
│   └── execute_buyback.py      # Execute token buyback
│
└── mocks/                      # Mock API services
    └── portfolio_api.py        # Portfolio analysis Mock
```

## Quick Start

### 1. Start Services

```bash
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
docker compose -f docker/docker-compose.yaml exec portfolio-risk-analyzer bash

# Run tests
python -c "from tools.analyze_portfolio import execute; print(execute('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'))"
```

### 3. Use MCP Service

MCP service runs at `http://localhost:8000` with SSE transport.

## Available Tools

| Tool | Description |
|------|-------------|
| `analyze_portfolio` | Full portfolio analysis with risk scores, breakdown, recommendations |
| `get_risk_breakdown` | Detailed risk breakdown (asset class, protocol, concentration, IL) |
| `run_stress_test` | Stress test scenarios (crash, liquidation, gas) |
| `get_optimization` | Optimization recommendations (rebalancing, hedging, yield) |
| `verify_payment` | Verify payment or $BANKR holding for service access |
| `execute_buyback` | Execute buyback of fees to $BANKR token |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORTFOLIO_API_BASE` | http://localhost:8001 | Portfolio Mock API |
| `MCP_TRANSPORT` | stdio | MCP transport (stdio or http) |

## Data Synthesis Workflow

### Step 1: Define Scenarios

```json
{
  "session_id": "session_001",
  "skill": "portfolio-risk-analyzer",
  "scenarios": [
    {
      "turn": 1,
      "user": "Analyze my portfolio 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "expected_tool": "analyze_portfolio",
      "expected_params": {"wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"}
    }
  ]
}
```

### Step 2: Tool Calls

```
User: Analyze my portfolio
Assistant: Let me analyze your portfolio.
[Calls: analyze_portfolio(wallet="0x...")]
```

### Step 3: Collect Trajectories

```json
{
  "session_id": "session_001",
  "turns": [
    {"role": "user", "content": "Analyze my portfolio"},
    {"role": "assistant", "content": "Let me analyze...", "tool_calls": [{"name": "analyze_portfolio", "arguments": {"wallet": "0x..."}}]},
    {"role": "tool", "name": "analyze_portfolio", "content": "## Portfolio Analysis..."}
  ]
}
```

## Notes

- All tools use Mock API returning preset data
- Mock data is static, suitable for tool selection training
- No real API keys required
- Data is time-independent, suitable for training at any time
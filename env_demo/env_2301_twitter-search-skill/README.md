# Twitter Search MCP Environment

MCP environment for Twitter/X social media search and analysis.

## Overview

This environment provides tools for searching Twitter using advanced search syntax and analyzing the results. It uses the TwitterAPI.io service pattern with a mock API for testing.

## Directory Layout

```
env_2301_twitter-search-skill/
├── SKILL.md                 # Original skill definition
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server with dynamic tool discovery
├── tools.jsonl              # Tool schemas (for blueprint generation)
├── test_tools.py            # Smoke tests
│
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   └── twitter_search.py    # Twitter search tool
│
├── docker/
│   ├── Dockerfile           # Container build
│   └── docker-compose.yaml  # Service orchestration
│
├── mocks/                   # Mock APIs
│   └── twitter_api.py       # TwitterAPI.io mock
│
└── README.md                # This file
```

## Tools

### twitter_search

Search Twitter for keywords using advanced search syntax and analyze results.

**Parameters:**
- `query` (required): Search query using Twitter syntax (e.g., "AI", "from:elonmusk", "#AI lang:en")
- `max_results` (optional): Max tweets to fetch (default: 100, max: 1000)
- `query_type` (optional): "Top" for relevance, "Latest" for recent (default: "Top")

**Returns:** Analysis report with tweet metrics, top tweets, hashtags, and author statistics.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | MCP transport mode ("http"/"sse" or stdio) | stdio |
| `TWITTER_API_BASE` | Twitter API endpoint | http://localhost:8003 |
| `TWITTER_API_KEY` | API key for TwitterAPI.io | mock-api-key |

## Running

### Docker (Recommended)

```bash
# Build and start
cd env_2301_twitter-search-skill
docker compose -f docker/docker-compose.yaml build
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

### Local Development

```bash
# Install dependencies
cd env_2301_twitter-search-skill
uv sync

# Start mock API
uvicorn mocks.twitter_api:app --port 8003 &

# Start MCP server (stdio mode)
python mcp_server.py
```

## Ports

- **8000**: MCP Server (HTTP/SSE mode)
- **8003**: Twitter Mock API

## Notes

- The mock API returns simulated tweet data for testing
- To use real Twitter API, set `TWITTER_API_BASE` to `https://api.twitterapi.io` and provide a valid `TWITTER_API_KEY`
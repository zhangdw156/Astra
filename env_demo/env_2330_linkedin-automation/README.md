# LinkedIn Automation MCP Environment

MCP environment for LinkedIn automation: posting, analytics, engagement, scheduling, and content ideas.

## Directory Layout

```
env_2330_linkedin-automation/
├── SKILL.md                 # Skill definition (copied from input)
├── pyproject.toml           # Python dependencies
├── mcp_server.py            # MCP server with dynamic tool discovery
├── tools.jsonl              # Tool schemas (for blueprint generation)
│
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── linkedin_post.py     # Post content to LinkedIn
│   ├── linkedin_analytics.py # Get analytics
│   ├── linkedin_ideas.py    # Generate content ideas
│   ├── linkedin_engage.py   # Engage with feed
│   └── linkedin_schedule.py # Schedule posts
│
└── docker/
    ├── Dockerfile           # Build image with uv
    └── docker-compose.yaml  # Service configuration
```

## Tools

| Tool | Description |
|------|-------------|
| `linkedin_post` | Post content to LinkedIn with optional image |
| `linkedin_analytics` | Get engagement stats (impressions, engagement rate, profile views) |
| `linkedin_ideas` | Generate content ideas based on topic |
| `linkedin_engage` | Like and comment on posts in feed |
| `linkedin_schedule` | Schedule a post for future publication |

## Prerequisites

- **Browser Tool**: This environment requires a browser tool (e.g., OpenClaw browser) to execute LinkedIn operations
- **LinkedIn Session**: Browser profile must have an active LinkedIn session logged in

## Running

### Local Development

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode for local/IDE use)
python mcp_server.py
```

### Docker

```bash
# Build and start
cd env_2330_linkedin-automation
docker compose -f docker/docker-compose.yaml build
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | MCP transport mode (`http`/`sse` or stdio) | stdio |
| `PYTHONPATH` | Python path | `/app` |

## MCP Port

- **MCP Server**: 8000 (when using HTTP transport)

## Notes

- This environment uses **browser automation** rather than LinkedIn API
- Tools return step-by-step browser instructions that should be executed by an agent using the browser tool
- LinkedIn enforces rate limits: 2-3 posts/day, 20-30 comments/day, 100 likes/day
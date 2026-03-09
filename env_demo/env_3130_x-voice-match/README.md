# X Voice Match - MCP Environment

Analyze Twitter/X accounts and generate authentic posts that match their voice.

## Directory Layout

```
env_3130_x-voice-match/
├── SKILL.md              # Original skill definition
├── pyproject.toml        # Python dependencies
├── mcp_server.py         # MCP server entry point
├── tools.jsonl           # Tool definitions for blueprint generation
├── test_tools.py         # Smoke tests
│
├── tools/                # MCP tool implementations
│   ├── __init__.py
│   ├── analyze_voice.py  # Analyze account voice profile
│   ├── generate_post.py  # Generate matching posts
│   └── quick_match.py    # One-step analyze + generate
│
└── docker/
    ├── Dockerfile        # Container build
    └── docker-compose.yaml
```

## Tools

| Tool | Description |
|------|-------------|
| `analyze_voice` | Analyze a Twitter/X account's posting style and generate a voice profile |
| `generate_post` | Generate posts matching a specific account's voice |
| `quick_match` | One-step voice matching: analyze + generate in one call |

## How to Run

### Local Development

```bash
cd /Users/zhangdw/work/lenovo/Astra/env_demo/env_3130_x-voice-match

# Install dependencies
uv sync

# Run MCP server (stdio mode for IDE)
python mcp_server.py

# Or HTTP/SSE mode
MCP_TRANSPORT=http python mcp_server.py
```

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

## MCP Endpoint

- **SSE Mode**: `http://localhost:8000`
- **Stdio Mode**: Default (for local/IDE use)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | Transport mode: `http`/`sse` or stdio | stdio |

## Testing

```bash
python test_tools.py
```

## Notes

This environment provides mock implementations for demonstration. The tools generate simulated voice profiles and posts. In production:
- `analyze_voice` would fetch real tweets via Bird CLI
- `generate_post` would use an LLM with the voice profile for generation
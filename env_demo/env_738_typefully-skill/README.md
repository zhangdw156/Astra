# Typefully MCP Environment

MCP environment for managing Typefully social media drafts via API.

## Directory Layout

```
env_738_typefully-skill/
├── SKILL.md                    # Original skill definition
├── pyproject.toml              # Python dependencies
├── mcp_server.py               # MCP server entry point
├── tools.jsonl                 # Tool schemas (JSONL)
├── test_tools.py               # Tool smoke tests
│
├── tools/                      # MCP tool implementations
│   ├── __init__.py
│   ├── list_drafts.py
│   ├── create_draft.py
│   ├── get_draft.py
│   ├── edit_draft.py
│   ├── schedule_draft.py
│   ├── delete_draft.py
│   └── list_social_sets.py
│
├── mocks/                      # Mock APIs (for testing without real API)
│   ├── __init__.py
│   └── typefully_api.py        # Typefully API mock
│
└── docker/
    ├── Dockerfile              # Container build
    └── docker-compose.yaml     # Service orchestration
```

## Tools

| Tool | Description |
|------|-------------|
| `list_drafts` | List Typefully drafts with optional status filter |
| `create_draft` | Create a new draft (supports threads, multi-platform) |
| `get_draft` | Get full details of a specific draft |
| `edit_draft` | Edit an existing draft |
| `schedule_draft` | Schedule or publish a draft |
| `delete_draft` | Delete a draft |
| `list_social_sets` | List available social sets (accounts) |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TYPEFULLY_API_KEY` | Typefully API key | `mock-api-key` |
| `TYPEFULLY_SOCIAL_SET_ID` | Social set ID | `123456` |
| `TYPEFULLY_API_BASE` | API base URL | `http://localhost:8001` |
| `MCP_TRANSPORT` | MCP transport (http/sse/stdio) | `stdio` |

## Running Locally

### With Docker

```bash
cd docker
docker compose build
docker compose up -d
```

### Local Development

```bash
# Install dependencies
uv sync

# Start Mock API
uvicorn mocks.typefully_api:app --port 8001 &

# Start MCP server
python mcp_server.py
```

## Ports

| Port | Service |
|------|---------|
| 8000 | MCP Server |
| 8001 | Typefully Mock API |

## Mock Data

The mock API includes:
- 2 social sets (123456, 789012)
- 3 pre-existing drafts (draft, scheduled, published)
- Support for all CRUD operations

## Usage with Real API

To use the real Typefully API instead of mocks:

```bash
export TYPEFULLY_API_KEY=your-api-key
export TYPEFULLY_SOCIAL_SET_ID=your-social-set-id
export TYPEFULLY_API_BASE=https://api.typefully.com/v2
python mcp_server.py
```
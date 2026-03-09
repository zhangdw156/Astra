# Typefully Drafts Skill - Complete Implementation

Typefully draft management MCP environment for multi-turn tool call data generation.

## Directory Structure

```
typefully-drafts/
├── SKILL.md                    # Original skill definition
├── docker/                     # Docker files
│   ├── Dockerfile
│   └── docker-compose.yaml
├── pyproject.toml              # Python dependencies (uv)
├── mcp_server.py               # MCP server entry
├── test_tools.py               # Tool test script
├── tools.jsonl                 # Tool definitions
│
├── tools/                      # MCP tool definitions
│   ├── __init__.py
│   ├── list_drafts.py          # List drafts
│   ├── create_draft.py         # Create draft
│   ├── get_draft.py            # Get draft details
│   ├── edit_draft.py           # Edit draft
│   ├── schedule_draft.py       # Schedule draft
│   ├── delete_draft.py         # Delete draft
│   └── list_social_sets.py     # List social accounts
│
└── mocks/                      # Mock API
    └── typefully_api.py        # Typefully Mock API
```

## Quick Start

### 1. Start Services

```bash
cd typefully-drafts

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
docker compose -f docker/docker-compose.yaml exec typefully-drafts bash

# Run tests
python test_tools.py
```

### 3. Use MCP Service

MCP service runs at `http://localhost:8000`, supports stdio and SSE modes.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_drafts` | List Typefully drafts (filter by status) |
| `create_draft` | Create a new draft (supports threads, multi-platform) |
| `get_draft` | Get draft details by ID |
| `edit_draft` | Edit existing draft content |
| `schedule_draft` | Schedule or publish a draft |
| `delete_draft` | Delete a draft |
| `list_social_sets` | List available social accounts |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPEFULLY_API_BASE` | http://localhost:8003 | Typefully Mock API |
| `TYPEFULLY_API_KEY` | mock-api-key | API Key |
| `TYPEFULLY_SOCIAL_SET_ID` | 123456 | Social set ID |

## Data Synthesis Workflow

### Step 1: Define Scenarios

```json
{
  "session_id": "session_001",
  "skill": "typefully-drafts",
  "scenarios": [
    {
      "turn": 1,
      "user": "Show me my recent drafts",
      "expected_tool": "list_drafts",
      "expected_params": {}
    },
    {
      "turn": 2,
      "user": "Create a new tweet about our new feature",
      "expected_tool": "create_draft",
      "expected_params": {"text": "Check out our new feature!"}
    }
  ]
}
```

### Step 2: Tool Invocation

LLM selects tools based on user input:

```
User: Show me my recent drafts
Assistant: Let me check your drafts.
[Calls: list_drafts(limit=10)]
```

### Step 3: Collect Trajectories

Record complete conversation trajectories:

```json
{
  "session_id": "session_001",
  "turns": [
    {"role": "user", "content": "Show me my recent drafts"},
    {"role": "assistant", "content": "Let me check your drafts.", "tool_calls": [{"name": "list_drafts", "arguments": {"limit": 10}}]},
    {"role": "tool", "name": "list_drafts", "content": "## Typefully Drafts\n\n..."}
  ]
}
```

## Notes

- All tool calls return mock data
- Mock data is static, suitable for training "tool selection" capability
- No real API key required
- Data is time-independent for training at any time
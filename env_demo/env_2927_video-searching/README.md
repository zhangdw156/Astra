# Video Searching Skill - Complete Implementation

Based on video-searching skill for multi-turn dialogue tool call data generation.

## Directory Structure

```
video-searching/
├── SKILL.md                    # Original skill definition
├── docker/                     # Docker related files
│   ├── Dockerfile              # Container image build
│   └── docker-compose.yaml    # Service orchestration
├── pyproject.toml              # Python dependencies (uv)
├── mcp_server.py               # MCP server entry
├── test_tools.py               # Tool test script
├── tools.jsonl                 # Tool definitions for blueprint
│
├── tools/                      # MCP tool definitions
│   ├── __init__.py
│   ├── video_search.py         # Search videos across platforms
│   ├── video_deterministic.py  # Deterministic /video_sourcing
│   ├── video_trending.py       # Get trending videos
│   └── video_compare.py        # Compare videos across platforms
│
└── mocks/                      # Mock API services
    └── video_api.py            # Video API Mock
```

## Quick Start

### 1. Start Services

```bash
# In video-searching directory
docker compose -f docker/docker-compose.yaml up -d

# View logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop services
docker compose -f docker/docker-compose.yaml down
```

### 2. Test Tools

```bash
# Enter container
docker compose -f docker/docker-compose.yaml exec video-searching bash

# Run tests
python test_tools.py
```

### 3. Use MCP Service

MCP service runs at `http://localhost:8000`, supports stdio and SSE mode.

## Available Tools

| Tool Name | Description |
|-----------|-------------|
| `video_search` | Search videos across YouTube, TikTok, Instagram, Twitter/X |
| `video_deterministic` | Run deterministic /video_sourcing command |
| `video_trending` | Get trending/popular videos |
| `video_compare` | Compare videos across multiple platforms |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEO_API_BASE` | http://localhost:8001 | Video API Mock address |
| `GOOGLE_API_KEY` | mock-api-key | Google API Key |
| `YOUTUBE_API_KEY` | mock-api-key | YouTube API Key |

## Data Synthesis Workflow

### Step 1: Prepare Scenarios

Define multi-turn dialogue scenarios:

```json
{
  "session_id": "session_001",
  "skill": "video-searching",
  "scenarios": [
    {
      "turn": 1,
      "user": "Find me some trending tech videos",
      "expected_tool": "video_trending",
      "expected_params": {"category": "tech"}
    },
    {
      "turn": 2,
      "user": "Compare these with music trending",
      "expected_tool": "video_compare",
      "expected_params": {"query": "music", "platforms": ["youtube", "tiktok"]}
    }
  ]
}
```

### Step 2: Call Tools

LLM selects tools based on user input:

```
User: Find me some trending tech videos
Assistant: Let me check the trending videos for you.
[Calls: video_trending(category="tech")]
```

### Step 3: Collect Trajectory

Record complete dialogue trajectory:

```json
{
  "session_id": "session_001",
  "turns": [
    {
      "role": "user",
      "content": "Find me some trending tech videos"
    },
    {
      "role": "assistant",
      "content": "Let me check the trending videos for you.",
      "tool_calls": [
        {
          "name": "video_trending",
          "arguments": {"category": "tech"}
        }
      ]
    },
    {
      "role": "tool",
      "name": "video_trending",
      "content": "## Trending Videos..."
    }
  ]
}
```

## Notes

- All tool calls return mock data from the Video API Mock
- Mock data is static, suitable for training "tool selection" capability
- No real API keys required
- Data is time-independent, suitable for training at any time
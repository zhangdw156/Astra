# Browser Use Local Environment

MCP environment for browser automation via browser-use CLI with session management, screenshots, HTML extraction, and LLM-powered agent.

## Directory Layout

```
env_4068_browser-use-local/
├── SKILL.md              # Original skill definition
├── pyproject.toml        # Python dependencies
├── mcp_server.py         # MCP server entry point
├── tools.jsonl           # Tool definitions (name, description, inputSchema)
├── test_tools.py         # Tool smoke tests
├── tools/                # MCP tool implementations
│   ├── __init__.py
│   ├── open_url.py       # Open URL in browser session
│   ├── get_state.py      # Get browser state (elements, URL, title)
│   ├── screenshot.py     # Take screenshot
│   ├── get_html.py       # Get page HTML
│   ├── evaluate_js.py    # Evaluate JavaScript
│   ├── run_agent.py      # Run browser-use agent with LLM
│   ├── crop_candidates.py  # Generate QR code crop candidates
│   └── extract_data_images.py # Extract data:image from HTML
└── docker/
    ├── Dockerfile        # Container build with browser-use
    └── docker-compose.yaml
```

## Tools

| Tool | Description |
|------|-------------|
| `open_url` | Open a URL in a browser session |
| `get_state` | Get current browser state (URL, title, elements) |
| `screenshot` | Take a screenshot of the current page |
| `get_html` | Get full HTML content (works when state is empty) |
| `evaluate_js` | Execute JavaScript in browser context |
| `run_agent` | Run browser-use agent with custom LLM |
| `crop_candidates` | Generate QR code crop candidates from screenshot |
| `extract_data_images` | Extract base64 images from HTML |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_TRANSPORT` | MCP transport mode (http/sse/stdio) | stdio |
| `BROWSER_USE_CLI` | Path to browser-use CLI | browser-use |
| `OPENAI_API_KEY` | API key for LLM (required for agent) | - |
| `OPENAI_BASE_URL` | Base URL for OpenAI-compatible LLM | https://api.moonshot.cn/v1 |

## Requirements

- Python 3.13+
- browser-use package
- Chromium browser (installed via playwright)
- OpenCV (for crop_candidates tool)

## How to Run

### Local Development

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode for IDE)
python mcp_server.py

# Or with HTTP transport
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

## Usage Examples

### Open a URL
```python
# Using the tool
result = open_url(url="https://example.com", session="demo")
```

### Take a Screenshot
```python
result = screenshot(path="/tmp/page.png", session="demo")
```

### Extract QR Code
```python
# First get HTML
get_html(session="demo")

# Then extract data:image
extract_data_images(html_path="/tmp/page_html.json", output_dir="/tmp/qr")
```

### Run Agent with Kimi
```bash
export OPENAI_API_KEY="your-kimi-key"
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"

# The run_agent tool will use these
```

## Notes

- Browser automation requires a supported browser (chromium recommended)
- Use persistent sessions (`--session name`) for multi-step flows
- Screenshot is the most reliable debugging primitive
- Use `get_html` when `get_state` returns 0 elements
- For agent runs, set `OPENAI_API_KEY` and `OPENAI_BASE_URL`
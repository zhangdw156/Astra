# Data Pods MCP Environment

Create and manage modular portable database pods with document ingestion and semantic search.

## Overview

This environment provides MCP tools for:
- Creating and managing portable SQLite-based data pods
- Adding notes with titles, content, and tags
- Ingesting documents (PDF, TXT, MD, DOCX, PNG, JPG) with embeddings
- Semantic search using sentence-transformers
- Consent layer for agent access control

## Directory Structure

```
env_1533_initv-data-pods/
├── SKILL.md              # Original skill definition
├── pyproject.toml        # Python dependencies
├── mcp_server.py         # MCP server entry (dynamic tool discovery)
├── tools.jsonl           # Tool schemas (JSONL format)
├── test_tools.py         # Smoke tests
│
├── tools/                # MCP tool implementations
│   ├── __init__.py
│   ├── create_pod.py     # Create new pod
│   ├── list_pods.py      # List all pods
│   ├── add_note.py       # Add note to pod
│   ├── query_pod.py      # Search notes
│   ├── export_pod.py     # Export pod as ZIP
│   ├── ingest_folder.py  # Ingest documents
│   ├── semantic_search.py # Semantic search
│   ├── list_documents.py # List ingested docs
│   ├── consent_grant.py  # Grant agent access
│   ├── consent_revoke.py # Revoke access
│   └── consent_status.py # Show consent status
│
└── docker/
    ├── Dockerfile        # Container build
    └── docker-compose.yaml
```

## Available Tools

| Tool | Description |
|------|-------------|
| `create_pod` | Create a new data pod (types: scholar, health, shared, projects) |
| `list_pods` | List all available pods |
| `add_note` | Add a note with title, content, tags |
| `query_pod` | Search notes by text or SQL |
| `export_pod` | Export pod as ZIP file |
| `ingest_folder` | Ingest documents from folder |
| `semantic_search` | Semantic search using embeddings |
| `list_documents` | List ingested documents |
| `consent_grant` | Grant agent access to pods |
| `consent_revoke` | Revoke agent access |
| `consent_status` | Show consent sessions |

## Storage Location

Data is stored in: `~/.openclaw/data-pods/`

## Running

### Local Development

```bash
# Install dependencies
uv sync

# Run MCP server (stdio mode)
python mcp_server.py

# Or with HTTP transport
MCP_TRANSPORT=http python mcp_server.py
```

### Docker

```bash
# Build
docker compose -f docker/docker-compose.yaml build

# Run
docker compose -f docker/docker-compose.yaml up -d

# Logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | stdio | Transport mode: stdio or http |
| `PYTHONPATH` | /app | Python path |

## Dependencies

Core:
- fastmcp >= 1.0
- fastapi >= 0.109.0
- uvicorn >= 0.27.0

Optional (for full functionality):
- PyPDF2 >= 3.0.0 (PDF extraction)
- python-docx >= 1.0.0 (DOCX extraction)
- Pillow >= 10.0.0 + pytesseract >= 0.3.10 (OCR)
- sentence-transformers >= 2.2.0 (embeddings)
- numpy >= 1.24.0 (math operations)

## Example Usage

```python
# Create a pod
create_pod(name="research", pod_type="scholar")

# Add notes
add_note(pod_name="research", title="Transformer Paper", content="...", tags="ai,nlp")

# Query
query_pod(pod_name="research", text="transformer")

# Ingest documents
ingest_folder(pod_name="research", folder_path="./papers", recursive=True)

# Semantic search
semantic_search(pod_name="research", query="attention mechanism", top_k=5)

# Export
export_pod(pod_name="research", output_path="./research.vpod")
```
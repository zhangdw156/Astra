# Memory Pioneer Skill - Environment

Environment for the memory-pioneer skill - an agent memory benchmarking tool.

## Directory Structure

```
memory-pioneer/
├── SKILL.md                    # Original skill definition
├── docker/                     # Docker files
│   ├── Dockerfile              # Container image build
│   └── docker-compose.yaml    # Service orchestration
├── pyproject.toml              # Python dependencies (uv)
├── mcp_server.py               # MCP server entry point
├── test_tools.py               # Tool smoke test script
├── tools.jsonl                 # Tool schema definitions
│
├── tools/                      # MCP tool implementations
│   ├── __init__.py
│   ├── collect_memory_stats.py  # Collect memory system statistics
│   ├── run_memory_assessment.py # Run retrieval quality assessment
│   ├── run_metric_tests.py      # Run IR metric unit tests
│   └── get_test_queries.py      # Get test query set
```

## Quick Start

### 1. Start Services

```bash
cd memory-pioneer

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
docker compose -f docker/docker-compose.yaml exec memory-pioneer bash

# Run tool tests
python test_tools.py
```

### 3. Use MCP Service

MCP service runs at `http://localhost:8000`, supports stdio and SSE modes.

## Available Tools

| Tool | Description |
|------|-------------|
| `collect_memory_stats` | Collect anonymized memory system statistics (counts, distributions, retrieval metrics) |
| `run_memory_assessment` | Run retrieval quality assessment with IR metrics (RAR, MRR, nDCG, MAP) |
| `run_metric_tests` | Run unit tests for IR metric calculations |
| `get_test_queries` | Get standardized test query set stratified by category and difficulty |

## What It Measures

- **Recall** - Does the agent remember what it stored?
- **Precision** - Does it retrieve the right things?
- **Hallucination rate** - Does it fabricate memories it never had?

## Metrics

The benchmark computes standard IR metrics:

- **RAR** (Recall Accuracy Ratio): Fraction of top-k results rated >= threshold
- **MRR** (Mean Reciprocal Rank): 1/rank of first relevant result
- **nDCG**: Normalized Discounted Cumulative Gain
- **MAP** (Mean Average Precision): Average precision across queries
- **Precision@k**: Precision at k results
- **Hit Rate**: Whether any relevant result was found

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | stdio | Transport mode (stdio, http, sse) |

## Data Synthesis Workflow

This environment is designed for the data-synthesis-workflow to generate multi-turn dialogue tool-calling data for agent memory benchmarking.

## Notes

- This skill works with local SQLite memory databases (no external APIs)
- Default database locations: `~/.openclaw/workspace/db/{memory,cognitive_memory,jarvis}.db`
- Assessment requires an existing memory database with stored memories
- Without a memory database, the tool will report that no data is available
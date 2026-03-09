# Generate Runnable Environment from Skill (OpenCode Prompt)

## IMPORTANT: Read Reference Example First

**Before generating**, you must **read and study** this reference example pair:

- **Reference skill (input)**: `{REF_SKILL_DIR}` — the source skill with SKILL.md and scripts
- **Reference environment (output)**: `{REF_ENV_DIR}` — the desired generated structure

Read at least these files in the reference environment:
- `mcp_server.py` — dynamic tool discovery pattern (scan tools/, register via add_tool)
- `tools/compare_markets.py` (or any tool) — TOOL_SCHEMA + sync execute()
- `docker/Dockerfile` — uv sync, uvicorn for mocks, MCP_TRANSPORT
- `docker/docker-compose.yaml` — port mapping, env vars
- `mocks/kalshi_api.py` (or any mock) — FastAPI endpoints matching tools

**Replicate the same patterns** (dynamic discovery, sync execute, uv-based Dockerfile, mock API structure) when generating. Do not hardcode tools or use async execute unless the reference does.

---

## Objective

You are an **environment generator**. Given a **skill directory** (e.g. `{SKILL_DIR}`: contains SKILL.md and optionally scripts, docs, etc.), produce a **runnable MCP environment directory** (e.g. `{ENV_DIR}`) such that:

1. Every **command/capability** described in the skill maps to at least one **MCP tool** callable by an Agent via MCP;
2. The environment can be **started locally or with Docker** and tool calls can run without real API keys (via Mock APIs);
3. The output layout and code style match the reference environment structure, so it fits into the data-synthesis-workflow blueprint and agent simulation pipeline.

---

## Input

| Input | Description |
|-------|-------------|
| **Skill directory path** | Path to the skill root, e.g. `{SKILL_DIR}` |
| **SKILL.md content** | Skill definition: `name`, `description`, `Commands`, `Output Format`, `Requirements`, `Example Usage` (YAML frontmatter + Markdown) |
| **Optional** | `scripts/` and other docs or examples under the same directory, used to infer command parameters and behavior |

---

## Output: Environment Directory Layout

Under the **target environment directory** `{ENV_DIR}` (one directory, name it from the skill name, e.g. strip any numeric prefix), generate the following layout:

```
<env_name>/
├── SKILL.md                 # Optional: copy from skill dir for traceability
├── pyproject.toml           # Python deps (fastmcp, fastapi, uvicorn, httpx, etc.)
├── mcp_server.py            # MCP server entry: scan tools/ and register all tools
├── tools.jsonl              # One JSON per line: name, description, inputSchema (for blueprint, etc.)
├── test_tools.py            # Optional: simple script that runs each tool execute() for smoke tests
│
├── tools/                   # MCP tool implementations
│   ├── __init__.py
│   ├── <tool_a>.py          # Each file: TOOL_SCHEMA + execute(...) -> str
│   ├── <tool_b>.py
│   └── ...
│
├── docker/
│   ├── Dockerfile           # Build image: install deps, copy tools/mocks/mcp_server, start MCP + Mock APIs
│   └── docker-compose.yaml  # Single service, expose MCP port (e.g. 8000) and Mock ports
│
├── mocks/                   # Only when the skill depends on external APIs
│   ├── <service_a>_api.py   # FastAPI app mocking external API, return preset data
│   └── ...
│
└── README.md                # Env description: layout, how to run, tool list, env vars
```

---

## Conventions

### 1. Mapping from SKILL to tools

- **SKILL.md Commands / Example Usage**: each user-invokable "command" or typical usage corresponds to one **MCP tool**.
- If one command has multiple parameter shapes (e.g. by platform and by topic), split into multiple tools (e.g. `kalshi_fed`, `kalshi_search`, `polymarket_trending`) so the Agent can choose by intent.
- Tool **name**: lowercase, underscores, and must match the file name (e.g. `compare_markets` → `tools/compare_markets.py`).

### 2. Tool modules (tools/*.py)

Each tool file must define:

- **TOOL_SCHEMA**: a dict with:
  - `name`: same as the file name;
  - `description`: one-sentence purpose, optionally including platform/domain (for LLM tool selection);
  - `inputSchema`: JSON Schema, `type: "object"`, `properties` and `required`; parameter names must match `execute` keyword arguments.
- **execute(...)**: function whose parameters match `inputSchema.properties`, returning **str** (usually Markdown or plain text for the Agent to show the user).

Do **not** hardcode URLs for external services. Read base URL from environment variables (e.g. `KALSHI_API_BASE`, `UNIFAI_API_BASE`), defaulting to the local Mock (e.g. `http://localhost:8002`), so the same code can talk to Mocks in Docker and to real APIs when env vars are overridden.

### 3. tools.jsonl

- One JSON object per line, no newlines inside the object.
- Fields: `name`, `description`, `inputSchema`, matching each `tools/*.py` `TOOL_SCHEMA`.
- Used by scripts such as task_blueprint_generator to build multi-turn dialogue blueprints and `tool_sequence`.

### 4. mcp_server.py

- Use **FastMCP**; service name should match the environment name (the value used for `{ENV_DIR}` / `<env_name>`).
- **Discovery**: scan all `.py` under `tools/` (skip `__init__.py` and names starting with `_`), load modules dynamically; if a module has `TOOL_SCHEMA` and `execute`, register it as an MCP tool.
- **Transport**: when env var `MCP_TRANSPORT=http` (or `sse`), use SSE and listen on 0.0.0.0:8000; otherwise use stdio for local or IDE use.

### 5. Docker

- **Dockerfile**: base image with uv/Python 3.13, copy `pyproject.toml`, `tools/`, `mocks/`, `mcp_server.py`; install deps; set `PYTHONPATH`, `MCP_TRANSPORT=http`, and Mock base URL env vars; in **CMD**, start Mock API processes first (e.g. uvicorn on multiple ports), then `python mcp_server.py`, then `wait` to keep the container running.
- **docker-compose.yaml**: single service, build context = environment root; map MCP port (e.g. 8000) and all Mock ports; optional healthcheck curling a Mock `/health` to ensure readiness.

### 6. Mock APIs (mocks/)

- If the skill **Requirements** mention external APIs (e.g. `UNIFAI_AGENT_API_KEY`, third-party data), provide **Mock implementations** for those dependencies.
- One FastAPI app per Mock (e.g. `mocks/kalshi_api.py`, `mocks/unifai_api.py`) with endpoints matching the paths used by the tools (e.g. `/markets/fed`, `/v1/agent/search`), returning **static or random but well-formed JSON** so tools and agent simulation run without real keys.
- Tools switch to Mocks via env vars (e.g. `KALSHI_API_BASE=http://localhost:8002`); inside Docker, Mocks and MCP run on the same host, so localhost is fine.

### 7. Environment variables and README

- In README, list: MCP port, Mock ports, and any env vars from the skill (e.g. API keys); note that in "Mock-only" mode a placeholder key is enough, and real keys are for connecting to real APIs.
- Documentation language is up to the project; the prompt itself is in English.

---

## Generation steps (recommended order)

1. **Parse SKILL.md**: extract name, description, Commands, Example Usage, Requirements.
2. **List tools**: for each command/usage, decide one tool name and parameters (inputSchema).
3. **Create tools/*.py**: implement TOOL_SCHEMA and execute(), with requests using env-configured base URLs.
4. **Emit tools.jsonl**: one line per tool from TOOL_SCHEMA (name, description, inputSchema).
5. **Write mcp_server.py**: generic discovery and registration (can follow the reference environment).
6. **If external APIs are needed**: implement Mocks under mocks/ and start them in Dockerfile CMD.
7. **Write docker/**: Dockerfile and docker-compose.yaml, exposing MCP and Mock ports.
8. **Write README.md**: directory layout, how to run, tool list, env vars.
9. **Validate and fix**: run the validation script and fix any failures before finishing.

---

## Quality gate: Validation (REQUIRED)

After generating the environment at `{ENV_DIR}`, you **must** run the validation script to ensure quality:

```bash
uv run python exps/data-synthesis-workflow/opencode_demo/validate_env.py {ENV_DIR}
```

- **Exit 0**: validation passed; the environment is ready.
- **Exit 1**: validation failed; read the printed error (structure / uv_sync / mcp_initialize) and **fix the issues**, then run the script again until it passes.

The script checks: (1) structure (mcp_server.py, tools/, pyproject.toml exist), (2) `uv sync --no-install-project` succeeds, (3) MCP server starts and responds to Initialize. Do not consider the task complete until validation passes.

---

## Reference implementation

When running, the following placeholders are filled:

| Placeholder | Meaning |
|-------------|---------|
| `{REF_SKILL_DIR}` | **Example skill** to study (read its structure and SKILL.md) |
| `{REF_ENV_DIR}` | **Example environment** to study (read mcp_server, tools, docker, mocks) |
| `{SKILL_DIR}` | **Your input**: the skill to transform |
| `{ENV_DIR}` | **Your output**: target directory for the generated environment |

Generate the environment at `{ENV_DIR}` from `{SKILL_DIR}`, replicating the patterns you observed in `{REF_ENV_DIR}`. The result should plug into the data-synthesis-workflow (blueprint generation, agent simulation).

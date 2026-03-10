# Generate Runnable Environment from Skill (OpenCode Prompt)

## IMPORTANT: Read Reference Example First

**Before generating**, you must **read and study** this reference example pair:

- **Reference skill (input)**: `{REF_SKILL_DIR}` — the source skill with SKILL.md and scripts
- **Reference environment (output)**: `{REF_ENV_DIR}` — the desired generated structure

Read at least these files in the reference environment:
- `state.py` — state access layer (read/write/transaction, ensure_schema_and_initial_data)
- `database/schema.sql` and `database/initial_data.sql` — SQLite state backend
- `mcp_server.py` — dynamic tool discovery (scan tools/, register via add_tool)
- `tools/compare_markets.py` (or any tool) — TOOL_SCHEMA + sync execute() **using state layer**, not HTTP
- `docker/Dockerfile` — uv sync, copy database/ and state.py, init DB on startup, then MCP + mocks
- `docker/docker-compose.yaml` — **only expose MCP server port (e.g. 8000)**; Mock ports are internal only
- `mocks/kalshi_api.py` (or any mock) — FastAPI app **reading from the same SQLite via state layer**

**Replicate the same patterns**: database-driven state, state access layer, tools and mocks both use state; dynamic discovery; sync execute; uv-based build and run; **docker-compose exposes only the MCP port**. Do not hardcode tools or use async execute unless the reference does.

When generating a new env, **copy reusable files** from the reference (e.g. `mcp_server.py`, `.dockerignore`, `scripts/export_tool_schemas.py`, then with substitution: `docker-compose.yaml`, `pyproject.toml`, `Dockerfile`) and **generate per skill** only `state.py`, `database/`, `tools/*.py`, `mocks/*.py`, `tools.jsonl`, `test_tools.py`, `README.md`. See **§10 Reusable vs skill-specific files** for the full list.

---

## Objective

You are an **environment generator**. Given a **skill directory** (e.g. `{SKILL_DIR}`: contains SKILL.md and optionally scripts, docs, etc.), produce a **runnable MCP environment directory** (e.g. `{ENV_DIR}`) such that:

1. Every **command/capability** described in the skill maps to at least one **MCP tool** callable by an Agent via MCP;
2. The environment uses a **SQLite state backend** and a **state access layer** so that tools and (optional) Mocks share the same state—deterministic, verifiable, reproducible, and concurrency-friendly;
3. The environment can be **started locally (with uv) or with Docker**, and tool calls run without real API keys; **Docker only exposes the MCP server port**;
4. The output layout and code style match the reference environment structure, so it fits into the data-synthesis-workflow blueprint and agent simulation pipeline.

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
├── database/                # SQLite state backend (required by design)
│   ├── schema.sql           # CREATE TABLE for entities used by tools
│   └── initial_data.sql     # INSERT seed data for reproducible state
├── state.py                 # State access layer: read/write/transaction, ensure_schema_and_initial_data()
├── pyproject.toml           # Python deps (fastmcp, fastapi, uvicorn, etc.; no requests if tools use state only)
├── mcp_server.py            # MCP server entry: scan tools/ and register all tools
├── tools.jsonl              # One JSON per line: name, description, inputSchema (for blueprint, etc.)
├── test_tools.py            # Calls ensure_schema_and_initial_data() then runs each tool execute() for smoke tests
│
├── tools/                   # MCP tool implementations (use state layer, not HTTP to mocks)
│   ├── __init__.py
│   ├── <tool_a>.py          # TOOL_SCHEMA + execute(...) -> str; inside: import state, state.read_*(...)
│   ├── <tool_b>.py
│   └── ...
│
├── docker/
│   ├── Dockerfile           # uv sync; copy database/, state.py, tools/, mocks/, mcp_server; init DB in CMD then start MCP + mocks
│   └── docker-compose.yaml  # Single service; expose ONLY MCP port (e.g. 8000); Mock ports stay internal
│
├── mocks/                   # Only when the skill depends on external APIs; read from same SQLite via state
│   ├── <service_a>_api.py   # FastAPI app that queries state layer (same DB as tools)
│   └── ...
│
└── README.md                # Env description: layout, how to run (uv / Docker), tool list, STATE_DB_PATH and env vars
```

---

## Conventions

### 1. Mapping from SKILL to tools

- **SKILL.md Commands / Example Usage**: each user-invokable "command" or typical usage corresponds to one **MCP tool**.
- If one command has multiple parameter shapes (e.g. by platform and by topic), split into multiple tools (e.g. `kalshi_fed`, `kalshi_search`, `polymarket_trending`) so the Agent can choose by intent.
- Tool **name**: lowercase, underscores, and must match the file name (e.g. `compare_markets` → `tools/compare_markets.py`).

### 2. State backend and state access layer (database/, state.py)

- **database/schema.sql**: Define SQLite tables for all entities the tools need (e.g. markets, events, users). Include indexes for frequent queries.
- Prefer a **two-layer state model** when the environment is intended for batch trajectory synthesis:
  - **Shared static tables**: read-only reference data shared by all runs (e.g. market catalogs, seed entities).
  - **Run-scoped tables**: tables keyed by `run_id` for trajectory metadata, tool call logs, state deltas, outputs, and snapshots.
- Two supported isolation modes:
  - **Mode A: dedicated DB per run** — better for strong state, complex transactions, or destructive writes.
  - **Mode B: shared DB + `run_id` isolation** — preferred for read-only or light-state environments and high-concurrency synthesis.
- **database/initial_data.sql**: INSERT seed data so that tools have deterministic, reproducible state. Use `INSERT OR REPLACE` where appropriate to avoid duplicates on re-init.
- **state.py**: Provide a state access layer used by both tools and mocks:
  - `read(table, where=..., order_by=..., limit=...)` — generic query returning list of dicts.
  - Domain helpers if useful (e.g. `read_kalshi_markets(category=..., search_query=..., limit=...)`, `read_polymarket_events(...)`).
  - `ensure_schema_and_initial_data()` — run schema.sql then initial_data.sql if DB is empty; call this at container startup and in test_tools.py so local runs work without manual DB setup.
- If using Mode B, `state.py` must also provide a **RunContext** abstraction (for example `run_context(run_id)` / `current_run_id()`) so run-scoped tables are automatically filtered by the current run.
- **Do not expose `run_id` in tool schemas**; it must be injected by the synthesis framework / state layer, not by the LLM agent as a user-visible argument.
- **STATE_DB_PATH** (env var): Path to the SQLite file; default e.g. `./data/state.db`; in Docker use a path under a mounted volume (e.g. `/app/data/state.db`).

### 3. Tool modules (tools/*.py)

Each tool file must define:

- **TOOL_SCHEMA**: a dict with:
  - `name`: same as the file name;
  - `description`: one-sentence purpose, optionally including platform/domain (for LLM tool selection);
  - `inputSchema`: JSON Schema, `type: "object"`, `properties` and `required`; parameter names must match `execute` keyword arguments.
- **execute(...)**: function whose parameters match `inputSchema.properties`, returning **str** (usually Markdown or plain text for the Agent to show the user).

**Tools must read/write state via the state access layer** (e.g. `from state import read_kalshi_markets` and use the returned data). Do **not** have tools call Mock APIs over HTTP; the design is database-driven so tools and mocks share the same SQLite. If the skill has no external API dependency, tools only need the state layer and no mocks are required.

For environments that support concurrent synthesis:
- tools may read shared static tables directly;
- any run-scoped write/log/snapshot operation must go through state-layer helpers that automatically bind the current `run_id`;
- tool code should remain business-focused and should not manually thread `run_id` through `TOOL_SCHEMA` parameters.

### 4. tools.jsonl

- One JSON object per line, no newlines inside the object.
- Fields: `name`, `description`, `inputSchema`, matching each `tools/*.py` `TOOL_SCHEMA`.
- Used by scripts such as task_blueprint_generator to build multi-turn dialogue blueprints and `tool_sequence`.

### 5. mcp_server.py

- Use **FastMCP**; service name should match the environment name (the value used for `{ENV_DIR}` / `<env_name>`).
- **Discovery**: scan all `.py` under `tools/` (skip `__init__.py` and names starting with `_`), load modules dynamically; if a module has `TOOL_SCHEMA` and `execute`, register it as an MCP tool.
- **Transport**: when env var `MCP_TRANSPORT=http` (or `sse`), use SSE and listen on 0.0.0.0:8000; otherwise use stdio for local or IDE use.

### 6. Docker

- **Dockerfile**: Base image with uv/Python 3.13. Copy `pyproject.toml`, `database/`, `state.py`, `tools/`, `mocks/` (if any), `mcp_server.py`. Run `uv sync --no-install-project`. Set `PYTHONPATH`, `STATE_DB_PATH`, `MCP_TRANSPORT=http`. In **CMD**: first run `python -c "from state import ensure_schema_and_initial_data; ensure_schema_and_initial_data()"`, then start Mock API(s) (e.g. uvicorn) and `python mcp_server.py`, then `wait`.
- **docker-compose.yaml**: Single service, build context = environment root. **Expose only the MCP server port** (e.g. `8000:8000`). Do **not** publish Mock API ports (8001, 8002, etc.) to the host—they run only inside the container for healthcheck or internal use. Optionally mount a volume or bind mount for `STATE_DB_PATH` so host-side simulation code and containerized tools can observe the same SQLite state. Healthcheck can curl a Mock's `/health` on localhost inside the container.

### 7. Mock APIs (mocks/)

- If the skill **Requirements** mention external APIs, provide **Mock implementations** that **read from the same SQLite state layer** (e.g. `from state import read_kalshi_markets`), so Mock responses and tool behavior share the same data. One FastAPI app per Mock with endpoints matching the paths that would be used by external callers (e.g. `/markets/fed`, `/health`). Mocks are optional when tools use only the state layer and no external client needs to hit Mock HTTP.

### 8. Environment variables and README

- In README, list: **MCP port only** (e.g. 8000)—mention that Docker exposes only this port; `STATE_DB_PATH`; and any env vars from the skill. Note that tools and mocks use the state backend, so no real API keys are needed for local/Docker runs.
- If Mode B is used, README must explicitly document:
  - what data is **shared static state**;
  - what data is **run-scoped state**;
  - how `run_id` is assigned and how outputs / snapshots are stored per run.
- Documentation language is up to the project; the prompt itself is in English.

### 9. Running with uv (local)

- The **local environment is assumed to have uv**. For any Python entrypoint (scripts, tests, validation), **prefer running with uv**: e.g. `uv run python test_tools.py`, `uv run python scripts/export_tool_schemas.py`, `uv sync` for install. In README and validation instructions, use `uv run python ...` so that the correct virtualenv and dependencies are used without requiring the user to activate a venv manually.

### 10. Reusable vs skill-specific files (copy from reference vs generate)

When creating a new environment from a skill, you can **copy some files directly from the reference environment** `{REF_ENV_DIR}` and **generate or adapt others** per skill. Use this classification:

| Category | Files | Action |
|----------|--------|--------|
| **Copy as-is** | `mcp_server.py`, `.dockerignore`, `.python-version`, `tools/__init__.py`, `scripts/export_tool_schemas.py` | Copy from reference; no edits. `mcp_server.py` uses the **current directory name** as MCP name, so it works in any env folder. |
| **Copy then substitute** | `docker/docker-compose.yaml`, `opencode.json.example`, `pyproject.toml` | Copy from reference, then replace placeholders: service name / container name / volume name / MCP key with **the new env directory name** (e.g. `env_2896_prediction-trader` → `env_1234_my-skill`); update `pyproject.toml` name and description for the new skill. |
| **Copy structure, adapt content** | `docker/Dockerfile` | Copy layout (base image, uv sync, COPY list, STATE_DB_PATH, init DB in CMD). Adapt: env vars and CMD lines for **which mock apps to start** (or omit mocks if the skill has none). |
| **Generate per skill** | `state.py`, `database/schema.sql`, `database/initial_data.sql`, `tools/*.py` (except `__init__.py`), `mocks/*.py`, `tools.jsonl`, `test_tools.py`, `README.md` | Do **not** copy from reference; create from SKILL.md and your state/tool design. Schema, state helpers, tool logic, mock endpoints, and tests are all skill-specific. Emit `tools.jsonl` from tool schemas (or run `scripts/export_tool_schemas.py` after creating tools). |

Do **not** copy `.venv/` or `uv.lock`; the new env should run `uv sync` to create its own venv and lockfile.

---

## Generation steps (recommended order)

1. **Parse SKILL.md**: extract name, description, Commands, Example Usage, Requirements.
2. **Plan state**: decide entities and tables (schema) and seed data (initial_data.sql) so tools have deterministic state.
3. **Create database/**: schema.sql and initial_data.sql; then **state.py** with read/write/transaction and ensure_schema_and_initial_data() (generate per skill; do not copy from reference).
4. **List tools**: for each command/usage, one tool name and parameters (inputSchema).
5. **Create tools/*.py**: TOOL_SCHEMA and execute() that **call the state layer**; add `tools/__init__.py` (copy from reference or minimal stub).
6. **Emit tools.jsonl**: one line per tool from TOOL_SCHEMA, or run `scripts/export_tool_schemas.py` after tools exist.
7. **Copy reusable files from reference**: copy **mcp_server.py**, **.dockerignore**, **.python-version**, **scripts/export_tool_schemas.py** from `{REF_ENV_DIR}` as-is (no edits). Copy **docker/docker-compose.yaml**, **opencode.json.example**, **pyproject.toml** then substitute the **new env directory name** for service names, MCP key, and project name/description. Copy **docker/Dockerfile** and adapt only the mock-related ENV and CMD lines for this skill’s mocks (or remove if no mocks).
8. **If external APIs are needed**: implement Mocks under mocks/ that **read from the state layer**; ensure Dockerfile CMD starts them.
9. **Write test_tools.py**: call ensure_schema_and_initial_data(), then run each tool execute() (skill-specific tool list).
10. **Write README.md**: directory layout, how to run with **uv** and Docker, tool list, STATE_DB_PATH and env vars; state that only MCP port is exposed.
11. **Validate and fix**: run the validation script with **uv run** and fix any failures before finishing.

---

## Quality gate: Validation (REQUIRED)

After generating the environment at `{ENV_DIR}`, you **must** run the validation script to ensure quality. **Use uv to run Python** (the local environment has uv):

```bash
uv run python exps/data-synthesis-workflow/opencode_demo/validate_env.py {ENV_DIR}
```

- **Exit 0**: validation passed; the environment is ready.
- **Exit 1**: validation failed; read the printed error (structure / uv_sync / mcp_initialize / database) and **fix the issues**, then run the script again until it passes.

The script checks: (1) structure (mcp_server.py, tools/, pyproject.toml, database/, state.py), (2) `uv sync --no-install-project` succeeds, (3) MCP server starts and responds to Initialize. Do not consider the task complete until validation passes. For local smoke tests, run `uv run python test_tools.py` from inside `{ENV_DIR}`.

---

## Reference implementation

When running, the following placeholders are filled:

| Placeholder | Meaning |
|-------------|---------|
| `{REF_SKILL_DIR}` | **Example skill** to study (read its structure and SKILL.md) |
| `{REF_ENV_DIR}` | **Example environment** to study (read mcp_server, tools, docker, mocks) |
| `{SKILL_DIR}` | **Your input**: the skill to transform |
| `{ENV_DIR}` | **Your output**: target directory for the generated environment |

Generate the environment at `{ENV_DIR}` from `{SKILL_DIR}`, replicating the patterns you observed in `{REF_ENV_DIR}`. The result should plug into the data-synthesis-workflow (blueprint generation, agent simulation). Remember: **each environment's docker-compose.yaml must only expose the MCP server port**; and when running any `.py` script locally, **prefer `uv run python ...`** so that uv manages the environment and dependencies.

# Generate tools.jsonl Only (Light / JSON-Only Pipeline)

## Purpose

For the **light data-synthesis pipeline**, the environment is **only** a single file: **tools.jsonl**.  
MCP server and tool execution are provided by the shared **astra** runner (started via Hydra with `tools_path`).  
No need to generate `mcp_server.py`, `docker/`, `tools/*.py`, `state.py`, or `database/`.

You are to produce **only** the file **tools.jsonl** at the output path `{OUTPUT_PATH}`.

---

## Input

| Input | Description |
|-------|-------------|
| **Skill directory** | `{SKILL_DIR}` — contains SKILL.md (name, description, Commands, Example Usage, Requirements) |
| **Output path** | `{OUTPUT_PATH}` — full path to the **single file** to write: `tools.jsonl` |

---

## Output: tools.jsonl

- **One JSON object per line** (no newlines inside the object).
- Each line must have:
  - **name**: tool name (lowercase, underscores), matching a command/capability from the skill.
  - **description**: one-sentence purpose for LLM tool selection.
  - **inputSchema**: JSON Schema object with `"type": "object"`, `"properties"`, and optionally `"required"`.

Example line:

```json
{"name": "search_markets", "description": "Search prediction markets by query.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}
```

- Map each **command or capability** in SKILL.md to **one or more tools** (e.g. one tool per platform or per action).
- Tool names must be unique. Prefer lowercase with underscores.

---

## Steps

1. Read **SKILL.md** in `{SKILL_DIR}`: extract Commands, Example Usage, Requirements.
2. List all tools: one tool per command/variant (name, short description, parameters as inputSchema).
3. Write **exactly one file**: `{OUTPUT_PATH}` (the path already points to the desired `tools.jsonl` file).
4. Ensure every line is valid JSON and contains `name`, `description`, and `inputSchema`.

---

## Validation

After writing the file, the caller will validate by:

1. Checking the file exists at `{OUTPUT_PATH}`.
2. Parsing each line as JSON and ensuring each object has `name` and at least `description` (and preferably `inputSchema`).

No Docker, no MCP server, no Python tool code are required for this pipeline. The synthesis runner will start a single MCP server with this `tools_path` when generating trajectories.

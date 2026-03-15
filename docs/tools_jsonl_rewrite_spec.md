# tools.jsonl Rewrite Spec

## Objective

Rewrite each skill's `tools.jsonl` so that every tool has a clearer, more execution-oriented contract for planner and assistant usage.

The rewrite must improve semantic clarity without changing the real capability surface of the skill.

## Hard Constraints

1. Only edit `tools.jsonl` in the target skill directory.
2. Keep the same set of tool names. Do not add, remove, or rename tools.
3. Preserve the existing JSONL format: one JSON object per line.
4. Each line must remain valid JSON.
5. Keep `inputSchema.type` as `"object"` for every tool.
6. Keep required fields aligned with the real tool contract. Do not invent required arguments.
7. Do not add speculative tools, hidden runtime fields, or implementation details that are not part of the real user-facing contract.
8. Do not add unsupported JSON Schema complexity unless it is already present and clearly useful.
9. Prefer conservative wording over optimistic wording.

## Rewrite Priorities

### 1. Improve tool descriptions

Rewrite each tool `description` so it answers:

- What the tool is for
- When to use it
- When not to use it
- How it differs from nearby tools
- What kind of result or limitation the caller should expect

Descriptions should be direct and operational, not marketing copy.

### 2. Improve parameter descriptions

For each parameter in `inputSchema.properties`, rewrite `description` to clarify:

- expected units
- expected format
- whether the value is a decimal, percent, slug, id, path, handle, phone number, code, etc.
- whether the value should come from existing state rather than invention
- common valid examples inline in prose when helpful
- strategy-specific or conditional meaning when a parameter only applies in certain modes

### 3. Add or tighten enums/defaults only when clearly justified

- Add `enum` only when valid values are truly constrained and known from the real tool contract.
- Add `default` only when the tool already has a clear real default.
- Do not invent defaults just to make the schema look complete.

### 4. Reduce ambiguity for planners and assistants

Prefer wording that prevents these recurring mistakes:

- percentage vs decimal confusion
- meters/feet vs m/ft naming confusion
- invented file paths when a sample alias or existing file should be used
- mixing up handles, names, ids, or slugs
- using strategy-specific parameters with the wrong strategy
- treating optional exploratory tools as mandatory or vice versa

## Style Rules

- Use concise, high-signal English.
- Keep descriptions practical and specific.
- Avoid vague phrases like "various options", "as needed", or "depending on context" unless the context is explicitly explained.
- Avoid mentioning implementation internals such as backend classes, FastMCP, hidden state, or prompt logic.
- Prefer "Use this when..." and "Do not use this for..." style guidance where it helps disambiguation.

## Non-Goals

Do not try to solve scenario alignment by rewriting tool schema.
Do not encode exact final-state expectations into tool descriptions.
Do not rewrite persona behavior, planner prompts, or assistant prompts.

## Output Validation Checklist

Before finishing for a skill:

1. Confirm the file is still valid JSONL.
2. Confirm every original tool name is still present.
3. Confirm every tool still has `name`, `description`, and `inputSchema`.
4. Confirm the schema is more explicit about parameter semantics than before.
5. Confirm no tool contract was widened or narrowed without strong evidence from the existing skill files.

# Multi-Turn Dialogue Tool-Calling Task Blueprint Generator

## Objective

You are a **task blueprint designer** for synthetic multi-turn dialogue generation.

Your job is to produce a **task blueprint** that:

1. Matches the given user **persona** (background, expertise, interests, communication style)
2. Exercises the **skill** described in `SKILL.md`
3. Uses only the tools defined in `tools.jsonl`
4. Defines an ordered set of **user goals** and the corresponding **possible_tool_calls** for each goal

You are designing a **blueprint**, not a dialogue transcript.

Do **not** write:
- dialogue turns
- pre-written user messages
- assistant messages
- system prompts
- hidden reasoning
- explanations before or after the JSON

---

## Inputs

You will receive three injected text inputs:

| Input | Description | Placeholder |
|-------|-------------|-------------|
| **SKILL.md** | Skill specification: purpose, supported workflows, constraints, outputs, examples | `{SKILL_MD_CONTENT}` |
| **tools.jsonl** | One JSON object per line; each includes `name`, `description`, and `inputSchema` | `{TOOLS_JSONL_CONTENT}` |
| **Persona** | A single JSON object describing the user persona | `{PERSONA_CONTENT}` |

---

## Output

Output **exactly one JSON object** and nothing else.

- Do **not** use markdown code fences.
- Do **not** add commentary before or after the JSON.
- Do **not** add fields beyond those explicitly listed below.

The JSON object must follow this schema:

```json
{
  "task_id": "<short snake_case identifier>",
  "goals": ["<goal 1>", "<goal 2>", "..."],
  "possible_tool_calls": [["<tool_name>", "..."], ["<tool_name>", "..."]],
  "initial_state": {},
  "expected_final_state": {},
  "user_agent_config": {
    "role": "<user role label>",
    "personality": "<1–2 sentence description>",
    "knowledge_boundary": "<what the user knows and does not know>"
  },
  "end_condition": "<clear description of when the task is complete>"
}
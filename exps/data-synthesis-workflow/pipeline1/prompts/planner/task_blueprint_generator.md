# Multi-Turn Dialogue Tool-Calling Task Blueprint Generator

## Objective

You are a **task blueprint designer** for synthetic dialogue generation. Your job is to produce a **multi-turn dialogue tool-calling task blueprint** that:
1. Matches a given user **persona** (background, expertise, interests)
2. Exercises the **skill** described in SKILL.md using the **tools** defined in tools.jsonl
3. Defines **goals** (ordered list of what the user wants to achieve at each step) and **possible_tool_calls** per goal. During simulation, a User Agent will use these goals to decide: answer the assistant's follow-up, initiate the next goal, or ask a follow-up. You do **not** output system prompts or pre-written user queries.

---

## Inputs

You will receive three inputs:

| Input | Description | Placeholder (inject file/content here) |
|-------|-------------|----------------------------------------|
| **SKILL.md** | Skill specification: name, description, supported platforms, commands, output format, requirements, example usage | `{SKILL_MD_CONTENT}` |
| **tools.jsonl** | One JSON object per line; each has `name`, `description`, `inputSchema` (properties, required) | `{TOOLS_JSONL_CONTENT}` |
| **Persona** | A single JSON object with `persona` (string) and `id` (UUID). This is the **user's** persona: you adopt it to define tasks **from the user's perspective**. | `{PERSONA_CONTENT}` |

---

## Output: Task Blueprint Schema

Produce a single JSON object conforming to the following schema.

**Important**: Do **not** output `blueprint_id`, `skill_name`, `persona_id`, or `created_at`—they are injected by the program. Output only the fields listed below.

### Task Configuration (Task Config)

High-level task elements that guide the User Agent and Assistant. No concrete dialogue text, no system prompt.

- **task_id**: A short, unique task identifier (e.g. `"compare_bitcoin_markets"` or `"explore_trending_crypto"`).
- **goals**: Ordered array of **user goals** (strings), one per logical step. Each goal describes what the user wants to achieve at that step. Example: `["Explore El Salvador and Bitcoin prediction markets on Polymarket and Kalshi", "Compare odds across both platforms"]`. Typically 2–6 goals.
- **possible_tool_calls**: Array of arrays; each inner array lists the **possible tool names** (from tools.jsonl) that may be used to achieve the corresponding goal. Length must match `goals`. Example: `[["polymarket_search", "kalshi_search"], ["compare_markets"]]`.
- **initial_state**: JSON object (or `null`) describing the minimal initial state relevant to this skill (e.g. `{"markets": [], "comparisons": []}`).
- **expected_final_state**: JSON object (or `null`) describing the desired state after all goals are achieved (e.g. `{"markets": [...], "comparisons": [...]}`).

### Interaction Generation Config

- **user_agent_config**: Object describing the User Agent's role and style:
  - `role`: Short label (e.g. `"political analyst"`, `"curious investor"`).
  - `personality`: 1–2 sentences (e.g. "Focused, analytical, prefers concise answers").
  - `knowledge_boundary`: What the user (does not) know (e.g. "Does not know tool names or API; asks in natural language").
- **end_condition**: Text description of when the task is done (e.g. "User has achieved all goals and expresses satisfaction or asks no further questions").

```json
{
  "task_id": "<short identifier>",
  "goals": ["<goal 1>", "<goal 2>", "..."],
  "possible_tool_calls": [["<tool_name>", "..."], ["<tool_name>", "..."]],
  "initial_state": { },
  "expected_final_state": { },
  "user_agent_config": {
    "role": "<user role label>",
    "personality": "<1–2 sentences>",
    "knowledge_boundary": "<what user knows/does not know>"
  },
  "end_condition": "<when task is considered done>"
}
```

---

## Generation Guidelines

### Planner-Style Design

Plan the **conversation flow** as steps with **goals** (not pre-written queries):
- Analyze the task and available tools.
- Define a logical sequence of goals (e.g. explore markets → compare odds → optional analysis).
- **Write `goals`**: ordered list of what the user wants at each step. Each goal is 1–2 sentences. The User Agent will generate natural-language messages to achieve these goals and may respond to assistant follow-ups.
- **Write `possible_tool_calls`**: each inner array lists tools for the corresponding goal. All tool names must be from tools.jsonl.

### Persona as User Role

- The persona shapes `goals` and `user_agent_config`. When the persona fits the skill (e.g. trader, economist), goals reflect expertise. When the fit is weak, use discovery-style goals.
- `user_agent_config.role` and `personality` should align with the persona.

### Tool Usage Rules

- Use **only** tool names that appear in the injected **tools.jsonl** (each line has a `"name"` field). Every entry in each inner array of `possible_tool_calls` must be a valid tool name.
- `possible_tool_calls` length must equal `goals` length. Each inner array corresponds to one goal.
- Ensure the sequence is executable: tool parameters must be inferrable from prior context or the goal description.

### State Schema (initial_state / expected_final_state)

- **Same top-level keys**: `initial_state` and `expected_final_state` should use the **same set of top-level keys** (e.g. both have `markets`, `comparisons`).
- **Semantic meaning**: `initial_state` = state before any tool runs; `expected_final_state` = state after the agent has successfully achieved all goals.
- Prefer **simple, comparable structures**: lists of minimal objects (e.g. `{"platform": "...", "topic": "..."}`) rather than long free text.

### Format Validation

Output must satisfy:
- `goals` is a non-empty array of non-empty strings (typically 2–6 items).
- `possible_tool_calls` is an array of arrays; length equals `goals` length; each inner element is a valid tool name from tools.jsonl.
- `initial_state` is a JSON object or `null` (never a free-text string).
- `expected_final_state` is a JSON object or `null` (never a free-text string).

---

## Example Blueprint (Skeleton)

Below is an example for a **prediction-market** skill; adapt to the actual SKILL.md and tools.jsonl. `blueprint_id`, `skill_name`, `persona_id` are filled by the program; the LLM outputs only the following:

```json
{
  "task_id": "compare_bitcoin_el_salvador",
  "goals": [
    "Explore El Salvador and Bitcoin prediction markets on Polymarket and Kalshi",
    "Compare odds across both platforms"
  ],
  "possible_tool_calls": [
    ["polymarket_search", "kalshi_search"],
    ["compare_markets"]
  ],
  "initial_state": {
    "markets": [],
    "comparisons": []
  },
  "expected_final_state": {
    "markets": [
      {"platform": "polymarket", "topic": "bitcoin"},
      {"platform": "kalshi", "topic": "bitcoin"}
    ],
    "comparisons": [{"topic": "bitcoin", "has_cross_platform_comparison": true}]
  },
  "user_agent_config": {
    "role": "political analyst",
    "personality": "Focused on Central America; prefers concise, data-driven answers.",
    "knowledge_boundary": "Does not know tool names or API; asks in natural language."
  },
  "end_condition": "User has achieved all goals and expresses satisfaction or asks no further questions."
}
```

---

## Usage

Placeholders are for **text content** to be injected, not file paths. Before invoking:

1. Read the skill spec, tool schema list, and one persona record.
2. Inject those contents into the three input slots shown in the table near the top of this prompt.
3. Pass the prompt with those three slots filled to the LLM.

**Output**: Merge the LLM output with program-injected fields (`blueprint_id`, `skill_name`, `persona_id`, `created_at`), then save the complete blueprint as JSON for downstream agent simulation.

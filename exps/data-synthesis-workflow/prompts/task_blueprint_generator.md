# Multi-Turn Dialogue Tool-Calling Task Blueprint Generator

## Objective

You are a **task blueprint designer** for synthetic dialogue generation. Your job is to produce a **multi-turn dialogue tool-calling task blueprint** that:
1. Matches a given user **persona** (background, expertise, interests)
2. Exercises the **skill** described in SKILL.md using the **tools** defined in tools.jsonl
3. Defines task intent, expected tool flow, and interaction config—**not** pre-written user queries. User messages will be **dynamically generated** by a User Agent during simulation, so you output a **task configuration** and **interaction generation config** only.

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

Produce a single JSON object conforming to the following schema. **Note**: `blueprint_id`, `skill_name`, and `persona_id` are **injected by the program**; do not generate them.

### Task Configuration (Task Config)

High-level task elements that guide what the User Agent and Assistant should achieve. No concrete dialogue text.

- **task_id**: A short, unique task identifier (e.g. `"compare_bitcoin_markets"` or `"explore_trending_crypto"`).
- **user_intent**: Abstract description of the user's goal in natural language. What does the user want to accomplish? One or two sentences. Example: "The user wants to explore prediction markets related to Bitcoin and El Salvador politics, then compare odds across Polymarket and Kalshi."
- **expected_tool_calls**: Ordered list of **tool names** (from tools.jsonl) the agent should call to complete the task. Only names; no arguments. Example: `["polymarket_search", "kalshi_search", "compare_markets"]`.
- **expected_final_state**: Text description of what the environment/database state should look like after task completion (e.g. "User has received market comparison results; no persistent state changes for read-only tasks").
- **expected_output**: Brief description of what the assistant's final reply should contain or accomplish (e.g. "Summary of Bitcoin-related markets from both platforms with odds comparison").

### Interaction Generation Config

Config for the dynamic User Agent and dialogue bounds.

- **system_message**: The **assistant's** system instruction for this task: role, capability, and how to use the skill/tools. One short paragraph. User-facing.
- **user_agent_config**: Object describing the User Agent's role and style:
  - `role`: Short label (e.g. `"political analyst"`, `"curious investor"`).
  - `personality`: 1–2 sentences (e.g. "Focused, analytical, prefers concise answers").
  - `knowledge_boundary`: What the user (does not) know (e.g. "Does not know tool names or API; asks in natural language").
- **max_turns**: Integer (e.g. 6–10). Maximum number of user turns before simulation stops.
- **end_condition**: Text description of when the task is done (e.g. "User has received comparison and expresses satisfaction or asks no further questions").

```json
{
  "task_id": "<short identifier>",
  "user_intent": "<abstract user goal, 1–2 sentences>",
  "expected_tool_calls": ["<tool_name>", "..."],
  "expected_final_state": "<text description of state after completion>",
  "expected_output": "<what the assistant's final reply should contain>",
  "system_message": "<assistant system instruction, one paragraph>",
  "user_agent_config": {
    "role": "<user role label>",
    "personality": "<1–2 sentences>",
    "knowledge_boundary": "<what user knows/does not know>"
  },
  "max_turns": 8,
  "end_condition": "<when task is considered done>"
}
```

---

## Generation Guidelines

### Planner-Style Design

Plan the **conversation flow** as steps, not scripts:
- Analyze the task intent and available tools.
- Define a logical sequence of steps (e.g. search → compare → analyze).
- Ensure `expected_tool_calls` reflects this sequence.
- Do **not** write specific user utterances; the User Agent will generate them dynamically.

### Persona as User Role

- The persona shapes `user_intent` and `user_agent_config`. When the persona fits the skill (e.g. trader, economist), intent and config should reflect expertise. When the fit is weak, use discovery-style intent.
- `user_agent_config.role` and `personality` should align with the persona.

### Tool Usage Rules

- Use only tool names listed in tools.jsonl (e.g. `"polymarket_search"`, `"compare_markets"`).
- `expected_tool_calls` is an ordered sequence. Early tools may be exploratory; later tools may drill down or compare.
- Ensure the sequence is executable: tool parameters must be inferrable from prior context or user intent.

### Format Validation

Output must satisfy:
- `user_intent` is clear and actionable.
- `expected_tool_calls` uses valid tool names from tools.jsonl.
- `expected_final_state` and `expected_output` are specific enough for validation.
- `max_turns` is a positive integer (typically 6–12).

---

## Example Blueprint (Skeleton)

`blueprint_id`, `skill_name`, `persona_id` are filled by the program; the LLM outputs only the following:

```json
{
  "task_id": "compare_bitcoin_el_salvador",
  "user_intent": "The user wants to explore prediction markets related to Bitcoin and El Salvador politics, then compare odds across Polymarket and Kalshi.",
  "expected_tool_calls": ["polymarket_search", "kalshi_search", "compare_markets"],
  "expected_final_state": "Read-only task; no persistent state changes. User has received market search and comparison results.",
  "expected_output": "Summary of Bitcoin and Salvadoran political markets from both platforms, with odds comparison.",
  "system_message": "You are an AI assistant for prediction market analysis. You have access to tools from Polymarket and Kalshi. Use the available tools to answer user questions about prediction markets.",
  "user_agent_config": {
    "role": "political analyst",
    "personality": "Focused on Central America; prefers concise, data-driven answers.",
    "knowledge_boundary": "Does not know tool names or API; asks in natural language."
  },
  "max_turns": 8,
  "end_condition": "User has received comparison results and expresses satisfaction or asks no further questions."
}
```

---

## Usage

Placeholders are for **text content** to be injected, not file paths. Before invoking:

1. Read the file contents and substitute:
   - `{SKILL_MD_CONTENT}` → full text of SKILL.md
   - `{TOOLS_JSONL_CONTENT}` → full text of tools.jsonl
   - `{PERSONA_CONTENT}` → one line from persona JSONL (e.g. from `persona/persona_5K.jsonl`)

2. Pass the prompt with all placeholders replaced by the actual content to the LLM.

**Output**: Merge the LLM output with program-injected fields (`blueprint_id`, `skill_name`, `persona_id`, `created_at`), then save the complete blueprint as JSON for downstream agent simulation.

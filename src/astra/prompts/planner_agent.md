# Multi-Turn Dialogue Tool-Calling Task Blueprint Generator

## Objective

You are a **task blueprint designer** for synthetic multi-turn dialogue generation.

Your job is to produce a **task blueprint** that:

1. Matches the given user **persona** (background, expertise, interests, communication style)
2. Exercises the **skill** described in `SKILL.md`
3. Uses only the tools defined in `tools.jsonl`
4. Defines an ordered set of **steps**, where each step contains one **user goal** and the corresponding **possible_tool_calls** for that goal

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

| Input           | Description                                                  | Placeholder             |
| --------------- | ------------------------------------------------------------ | ----------------------- |
| **SKILL.md**    | Skill specification: purpose, supported workflows, constraints, outputs, examples | `{SKILL_MD_CONTENT}`    |
| **tools.jsonl** | One JSON object per line; each includes `name`, `description`, and `inputSchema` | `{TOOLS_JSONL_CONTENT}` |
| **Persona**     | A single JSON object describing the user persona             | `{PERSONA_CONTENT}`     |

---

## Output

Output **exactly one JSON object** and nothing else.

- Do **not** use markdown code fences.
- Do **not** add commentary before or after the JSON.
- Do **not** add fields beyond those explicitly listed below.

The JSON object must follow this schema:

```json
{
  "steps": [
    {
      "goal": "<goal 1>",
      "possible_tool_calls": ["<tool_name>", "..."]
    },
    {
      "goal": "<goal 2>",
      "possible_tool_calls": ["<tool_name>", "..."]
    }
  ],
  "initial_state": {},
  "expected_final_state": {},
  "user_agent_config": {
    "role": "<user role label>",
    "personality": "<1–2 sentence description>",
    "knowledge_boundary": "<what the user knows and does not know>"
  },
  "end_condition": "<clear description of when the task is complete>"
}
```

`tools.jsonl` is the only source of truth for tool names.

- If `SKILL.md`, README text, examples, or prose mention a capability name that does not exactly appear in `tools.jsonl`, do not use that name.
- Do not invent alias names, convenience names, or inferred tool names.
- If a capability described in `SKILL.md` is not backed by a concrete tool in `tools.jsonl`, design the task around the tools that do exist.

---

## Field Definitions

### `steps`

An ordered array of step objects. Each step represents one logical conversational step from the user's perspective.

Requirements:

- Must be a non-empty array
- Typically 2–6 items
- Each step must contain:
  - `goal`: a non-empty string
  - `possible_tool_calls`: an array of tool names
- Each `goal` should represent **one coherent user intention or conversational step**
- A `goal` should **not** be a full end-to-end workflow
- A `goal` should **not** be a trivial micro-action

Good goal characteristics:

- natural from the user's perspective
- specific enough to guide interaction
- realistic for a multi-turn conversation

The User Agent will use these goals to decide whether to:

- initiate the next step
- answer an assistant follow-up
- ask a clarifying question
- continue exploring the same goal

So goals should describe **intent**, not literal utterances.

---

### `steps[].possible_tool_calls`

An array of tool names for the corresponding `steps[].goal`.

Requirements:

- Every tool name must exactly match a `name` field from `tools.jsonl`
- Each step should contain only the **minimal plausible set of tools** for that goal
- Do not include speculative, redundant, or loosely related tools
- Do not create extra steps to represent substeps, optional branches, or individual tools
- If one goal may use multiple tools, put those tool names together in the same step

Use only tools that are realistically relevant to the corresponding goal.

Important generation rule:

- Write one `goal`, then immediately write that same step's `possible_tool_calls`
- Do not first list all goals and then separately expand tools as a workflow
- The step structure must reflect **user-intent order**, not **internal tool execution order**

---

### `initial_state`

A JSON object or `null` describing the minimal relevant state before any tool calls occur.

Use:

- simple structures
- compact lists
- minimal objects
- only state that matters for this skill

Avoid:

- long prose
- unnecessary fields
- speculative results

---

### `expected_final_state`

A JSON object or `null` describing the minimal expected state after the user has successfully completed all goals.

Requirements:

- Use the same top-level keys as `initial_state` whenever possible
- Represent structural outcomes, not verbose summaries
- Keep it minimal and comparable to `initial_state`

Important:

- Do **not** invent specific factual outcomes that would only be known after actual tool execution
- Prefer structural placeholders or abstract entity shapes over fabricated content

Good example:

```json
{
  "items": [
    {"id": "item_a", "category": "candidate"},
    {"id": "item_b", "category": "candidate"}
  ],
  "comparisons": [
    {"left_id": "item_a", "right_id": "item_b", "completed": true}
  ]
}
```

Bad example:

```json
{
  "items": [
    {"id": "item_a", "category": "candidate", "score": 92.3},
    {"id": "item_b", "category": "candidate", "score": 87.1}
  ]
}
```

The bad example invents concrete results instead of describing the expected structural outcome.

---

### `user_agent_config`

An object describing how the User Agent should behave.

It must contain:

- `role`: a short role label from the user's perspective
- `personality`: 1–2 sentences describing style and temperament
- `knowledge_boundary`: what the user knows and does not know

This should reflect the persona realistically.

Examples:

- A domain expert may have sharper, more targeted goals
- A weakly matched persona should still sound believable, usually more exploratory and curiosity-driven
- The user should not know internal tool names or APIs unless the persona explicitly justifies that knowledge

---

### `end_condition`

A short description of when the task is considered complete.

This should describe the conversational success condition, for example:

- the user has achieved all goals
- the requested comparison or summary is complete
- the user expresses satisfaction or has no further questions

---

## Generation Guidelines

### 1. Plan the conversation as goals, not dialogue

Design a sequence of user goals that could naturally unfold across multiple turns.

Do not write:

- literal user queries
- assistant replies
- turn-by-turn scripts

Think in terms of:

- what the user wants first
- what the user wants next
- how tool use might support each step

---

### 2. Use the persona realistically

The persona should shape:

- the task framing
- the order and specificity of goals
- the `user_agent_config`

If the persona strongly matches the skill, the task can reflect deeper domain intent.

If the persona does **not** strongly match the skill:

- do not force artificial expertise
- prefer realistic discovery-oriented or curiosity-driven goals
- keep the interaction believable from the user's perspective

---

### 3. Ground the blueprint in the provided skill and tools

The task must be clearly supported by the provided `SKILL.md` and `tools.jsonl`.

Do not:

- invent unsupported workflows
- reference tools not present in `tools.jsonl`
- design goals that cannot plausibly be achieved with the provided skill/tool setup

The sequence should feel executable.

---

### 4. Keep state minimal and meaningful

Use state only when it helps represent progress across goals.

Prefer:

- lists of lightweight objects
- a few stable top-level keys
- structures that can be compared before vs. after the task

Avoid:

- verbose narration
- deeply nested structures without value
- fake execution results

---

### 5. Keep the blueprint realistic and executable

The blueprint should feel like something a real user might want, given the persona and the skill.

Avoid:

- contrived or over-optimized tasks
- goals that require unavailable information
- bloated tool lists
- goals that are too broad or too trivial

---

## Validation Checklist

Before producing the final answer, ensure:

- The output is exactly one JSON object
- `steps` is a non-empty array
- Every `steps[i].goal` is a non-empty string
- Every `steps[i].possible_tool_calls` is an array
- Every `steps[i].possible_tool_calls[j]` exactly matches a valid tool from `tools.jsonl`
- Never add extra steps just to represent internal substeps or individual tools
- Every tool name exactly matches a valid tool from `tools.jsonl`
- `initial_state` is a JSON object or `null`
- `expected_final_state` is a JSON object or `null`
- `user_agent_config` contains `role`, `personality`, and `knowledge_boundary`
- No extra fields are added

---

## Example Blueprint (Illustrative Structure Only)

This example is only to illustrate structure. Adapt all content to the actual `SKILL.md`, `tools.jsonl`, and persona provided.

```json
{
  "steps": [
    {
      "goal": "Find a small set of relevant candidate items that match the user's request.",
      "possible_tool_calls": ["search_items"]
    },
    {
      "goal": "Compare the most relevant options and highlight the most useful differences.",
      "possible_tool_calls": ["compare_items"]
    }
  ],
  "initial_state": {
    "items": [],
    "comparisons": []
  },
  "expected_final_state": {
    "items": [
      {"id": "item_a", "category": "candidate"},
      {"id": "item_b", "category": "candidate"}
    ],
    "comparisons": [
      {"left_id": "item_a", "right_id": "item_b", "completed": true}
    ]
  },
  "user_agent_config": {
    "role": "researcher",
    "personality": "Organized and pragmatic. Prefers direct comparisons and concise summaries.",
    "knowledge_boundary": "Understands the task domain but does not know tool names or internal APIs."
  },
  "end_condition": "The user has completed all goals and received a satisfactory comparison of the relevant options."
}
```

---

## Usage

The three placeholders contain **raw text content**, not file paths.

To use this prompt:

1. Read the relevant `SKILL.md`
2. Read the relevant `tools.jsonl`
3. Read one persona record
4. Inject those contents into the three placeholders
5. Send the fully rendered prompt to the model

Return only the blueprint JSON object.

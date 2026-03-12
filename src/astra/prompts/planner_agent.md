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
```

---

## Field Definitions

`goals`

An ordered array of user goals, one per logical conversational step.

Requirements:

- Must be a non-empty array
- Typically 2–6 items
- Each goal must be a non-empty string
- Each goal should represent **one coherent user intention or conversational step**
- A goal should **not** be a full end-to-end workflow
- A goal should **not** be a trivial micro-action

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

`possible_tool_calls`

An array of arrays. Each inner array lists the tool names that may be used to achieve the corresponding goal.

Requirements:

- Length must exactly equal the length of `goals`
- Every tool name must exactly match a `name` field from `tools.jsonl`
- Each inner array should contain only the **minimal plausible set of tools** for that goal
- Do not include speculative, redundant, or loosely related tools

Use only tools that are realistically relevant to the corresponding goal.

---

`initial_state`

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

`expected_final_state`

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
  "markets": [
    {"platform": "polymarket", "topic": "bitcoin"},
    {"platform": "kalshi", "topic": "bitcoin"}
  ],
  "comparisons": [
    {"topic": "bitcoin", "has_cross_platform_comparison": true}
  ]
}
```

Bad example:

```json
{
  "markets": [
    {"platform": "polymarket", "topic": "bitcoin", "odds": "62%"},
    {"platform": "kalshi", "topic": "bitcoin", "odds": "57%"}
  ]
}
```

The bad example invents concrete results instead of describing the expected structural outcome.

---

`user_agent_config`

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

`end_condition`

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

## Validation Checklist

Before producing the final answer, ensure:

- The output is exactly one JSON object
- `goals` is a non-empty array of non-empty strings
- `possible_tool_calls` is an array of arrays
- `possible_tool_calls` has the same length as `goals`
- Every tool name exactly matches a valid tool from `tools.jsonl`
- `initial_state` is a JSON object or `null`
- `expected_final_state` is a JSON object or `null`
- `user_agent_config` contains `role`, `personality`, and `knowledge_boundary`
- No extra fields are added

---

## Example Blueprint (Illustrative Structure Only)

This example is only to illustrate the structure. Adapt all content to the actual `SKILL.md`, `tools.jsonl`, and persona provided.

```json
{
  "goals": [
    "Explore relevant Bitcoin-related prediction markets across the supported platforms.",
    "Compare the available market coverage and identify where the same topic appears on multiple platforms."
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
    "comparisons": [
      {"topic": "bitcoin", "has_cross_platform_comparison": true}
    ]
  },
  "user_agent_config": {
    "role": "policy analyst",
    "personality": "Analytical and concise. Prefers evidence-backed summaries and direct comparisons.",
    "knowledge_boundary": "Understands the topic domain but does not know tool names or internal APIs."
  },
  "end_condition": "The user has completed all goals and received a satisfactory comparison of the relevant markets."
}
```

## Usage

The three placeholders contain raw text content, not file paths.

To use this prompt:

- Read the relevant `SKILL.md`
- Read the relevant `tools.jsonl`
- Read one persona record
- Inject those contents into the three placeholders
- Send the fully rendered prompt to the model

Return only the blueprint JSON object.
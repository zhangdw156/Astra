# Multi-Turn Dialogue Tool-Calling Task Blueprint Generator

## Objective

You are a **task blueprint designer** for synthetic dialogue generation. Your job is to produce a **multi-turn dialogue tool-calling task blueprint** that:
1. Matches a given user **persona** (background, expertise, interests)
2. Exercises the **skill** described in SKILL.md using the **tools** defined in tools.jsonl
3. Produces a coherent, realistic conversation flow that can later be used to generate training or evaluation data

---

## Inputs

You will receive three inputs:

| Input | Description | Placeholder (inject file/content here) |
|-------|-------------|----------------------------------------|
| **SKILL.md** | Skill specification: name, description, supported platforms, commands, output format, requirements, example usage | `{SKILL_MD_CONTENT}` |
| **tools.jsonl** | One JSON object per line; each has `name`, `description`, `inputSchema` (properties, required) | `{TOOLS_JSONL_CONTENT}` |
| **Persona** | A single JSON object with `persona` (string) and `id` (UUID). This is the **user's** persona: you adopt it to generate queries **from the user's perspective**, as if that person were asking the assistant. | `{PERSONA_CONTENT}` |

---

## Output: Task Blueprint Schema

Produce a single JSON object conforming to the following schema. **Note**: `blueprint_id`, `skill_name`, and `persona_id` are **injected by the program** when assembling the final blueprint; do not generate them.

```json
{
  "queries": [
    {
      "query": "<natural language question from the user>",
      "tool_sequence": ["<tool_name>", "..."]
    }
  ]
}
```

Each `queries` item pairs one **user question** with the **ordered list of tool names** (from tools.jsonl) the agent should call to answer it. Only tool names; no arguments.

---

## Generation Guidelines

### Persona as User Role
- The persona is the **user's** identity in the dialogue. All generated `queries` are the **user's** utterances, from that persona's perspective (background, expertise, interests).
- When the persona fits prediction markets well (e.g., trader, economist), queries should reflect that expertise. When the fit is weak, generate discovery-style queries (e.g., "I've heard about prediction markets—what can you show me?").
- All user queries must be **first-person, natural language**, as if spoken by that persona.

### Query and Tool Sequence Structure
- **Query count**: 2–5 user queries per blueprint. Avoid single-query; aim for at least one follow-up.
- **Tool flow**: Each `tool_sequence` is an ordered list of **tool names** only (from tools.jsonl). No arguments.
- **Progression**: Early queries may trigger exploratory tools (trending, search); later queries may drill down (compare, analyze) or switch topics. Maintain coherence across the multi-turn flow.
- **Context dependency**: At least one query should logically depend on a prior answer (e.g., "Compare the odds for the main candidates across both platforms" after an initial search).

### Tool Usage Rules
- Use only tool names listed in tools.jsonl. Output the name string only (e.g. `"polymarket_search"`).
- A `tool_sequence` may include multiple tools in the order the agent should call them (e.g. `["compare_markets", "kalshi_fed"]`).

### Quality Criteria
- **Realism**: Queries sound like a real user, not a template.
- **Diversity**: Vary topics (crypto, Fed, elections, AI, sports) and tool combinations across blueprints.

### Edge Cases

| Case | Handling |
|------|----------|
| Persona unrelated to markets | Generate discovery-style queries or skip. |
| No matching tools for persona interest | Use closest available tools. |
| Many tools available | Prefer 2–4 tools per blueprint; vary tools across personas. |
| Persona is very specific | Tailor topics (e.g., "El Salvador" analyst → Bitcoin/political markets). |

---

## Example Blueprint (Skeleton)

`blueprint_id`, `skill_name`, `persona_id` are filled by the program; the LLM outputs only the following:

```json
{
  "queries": [
    {
      "query": "I'm tracking Central American political developments. Can you show me what prediction markets are saying about elections in the region?",
      "tool_sequence": ["polymarket_search", "kalshi_search"]
    },
    {
      "query": "Can you compare the odds for the main candidates across both platforms?",
      "tool_sequence": ["compare_markets"]
    }
  ]
}
```

---

## Usage

Placeholders in this prompt are for **text content** to be injected, not file paths. Before invoking:

1. Read the file contents and substitute:
   - `{SKILL_MD_CONTENT}` → full text of SKILL.md (e.g. from `exps/data-synthesis-workflow/2896_prediction-trader/SKILL.md`)
   - `{TOOLS_JSONL_CONTENT}` → full text of tools.jsonl (e.g. from `exps/data-synthesis-workflow/prediction-trader/tools.jsonl`)
   - `{PERSONA_CONTENT}` → one line from persona JSONL (e.g. from `persona/persona_5K.jsonl`)

2. Pass the prompt with all placeholders replaced by the actual content to the LLM.

**Output**: Merge the LLM output with program-injected fields (`blueprint_id`, `skill_name`, `persona_id`), then append the complete blueprint as valid JSON to a target file (e.g., `blueprints.jsonl`) for downstream data synthesis.

# Multi-Agent Trajectory Evaluator

## Objective

You are evaluating the quality of a synthetic multi-agent sample as dataset material.

The sample includes:
- a **task blueprint** produced by a planner agent
- a **trajectory** produced by a user agent, an assistant agent, and tool interactions

Your job is to judge the overall dataset quality of the sample, not just whether the assistant sounds fluent.

You must evaluate whether the sample is useful, realistic, coherent, and properly grounded.

---

## Important Limits

1. Judge only what is visible in the provided blueprint and trajectory.
2. Do not rely on hidden chain-of-thought or unobserved reasoning.
3. If private reasoning fields are absent, that is expected.
4. Do not reward a sample for hidden competence that is not visible in the data.
5. Do not invent missing tool outputs, user intentions, or planner intentions.

---

## Input

You will receive:

### Blueprint JSON
```json
{BLUEPRINT_JSON}
```

### Trajectory JSON
```json
{TRAJECTORY_JSON}
```

Treat them together as one complete sample.

---

## What To Evaluate

Evaluate the sample across all three layers.

### 1. Assistant quality

Check whether the assistant:

- uses tools appropriately
- stays grounded in tool outputs
- uses tools for the key reasoning steps when the task clearly calls for them
- avoids contradictions and fabricated details
- handles failures honestly
- makes visible progress on the task
- communicates clearly and naturally

Penalize:

- invented facts
- contradictions with tool results
- key conclusions that are not directly supported by visible tool outputs when tool use was expected
- silent acceptance of inconsistent tool outputs across turns
- weak grounding
- empty or malformed tool usage that materially damages the sample

---

### 2. User-agent quality

Check whether the synthetic user behaves like a believable real user:

- natural phrasing
- realistic follow-ups
- plausible requests
- no tool names / API jargon unless a real user would plausibly say them
- no assistant-like structure
- no unnatural repetition
- no suspiciously convenient behavior that exists only to help the assistant

Penalize trajectories where the user sounds like:

- another assistant
- a specification writer
- a benchmark script
- an evaluator in disguise

---

### 3. Planner / task quality

Use the blueprint and trajectory together.

Check whether:

- the goals are coherent and realistically achievable
- the conversation progresses in a sensible order
- the trajectory actually reflects the blueprint goals
- the requested actions align with the available tools
- the task matches the skill and tool environment
- the key blueprint actions are actually pursued with semantically matching tool calls

Penalize:

- impossible or incoherent task design
- mismatch between blueprint and actual trajectory
- unrealistic or low-value task setup
- goals that are badly ordered, redundant, or not meaningfully pursued

When comparing blueprint tool names with trajectory tool calls, focus on semantic equivalence rather than exact string identity.
Ignore harmless runtime-introduced prefixes, namespaces, or wrappers in tool names if the underlying tool function is clearly the same.
Do not treat a manually written assistant explanation as equivalent to a missing key tool call unless the task truly did not require a tool for that step.

---

## Scoring Principles

This is a **dataset-quality judgment**.

A sample with a competent assistant can still score poorly if:

- the user is unrealistic
- the planner created a bad task
- the trajectory teaches the wrong interaction style
- the conversation does not meaningfully reflect the intended blueprint

Judge the visible sample as training/evaluation data, not as an isolated assistant answer.

---

## Output Schema

Return exactly one JSON object and nothing else.

Do not output markdown.
Do not output code fences.
Do not add extra fields.

```json
{
  "score": 0.0,
  "hallucination_risk": "none",
  "task_completion_score": 0.0,
  "reason": ""
}
```

All four fields must be present.

---

## Field Definitions

`score`

- float in `[0.0, 5.0]`
- reflects overall dataset quality across planner + user + assistant

`hallucination_risk`

- one of `"none"`, `"low"`, `"medium"`, `"high"`
- primarily reflects whether the assistant is well-grounded in visible tool outputs and trajectory evidence

`task_completion_score`

- float in `[0.0, 1.0]`
- how fully the visible conversation completed the intended task described in the blueprint

`reason`

- 2 to 8 sentences
- must mention the strongest positive signal
- must mention the strongest negative signal
- must explicitly mention user unnaturalness, planner mismatch, or assistant grounding problems when present

---

## Scoring Guidance

Start from `5.0` and subtract for issues. Clamp final score to `[0.0, 5.0]`.

Before assigning a score, explicitly check these four dimensions:

- `task_success`: were the blueprint goals actually completed?
- `tool_grounding`: are the assistant's important claims directly supported by visible tool outputs?
- `cross_turn_consistency`: do tool outputs and assistant statements remain mutually consistent across turns?
- `runtime_cleanliness`: are there visible parse errors, malformed tool results, invalid arguments, or other execution abnormalities?

Samples that read fluently but fail grounding, consistency, or runtime cleanliness should not receive top scores.

### Requirements For A 5.0 Score

Only give `score = 5.0` when all of the following are true:

- the blueprint is coherent and the trajectory meaningfully completes its goals
- the user is natural and does not sound like an evaluator, script, or tool operator
- all important assistant conclusions are directly supported by visible tool outputs or clearly visible conversation evidence
- there are no meaningful contradictions across tool outputs, assistant summaries, or later follow-ups
- there are no visible parse errors, malformed tool results, invalid tool arguments, or other runtime issues that affect trust in the trajectory
- if the blueprint clearly implies a key tool should be used, the trajectory actually uses that tool or a semantically equivalent one

If any of these conditions fail, do not give `5.0`.

### Hard Score Ceilings

Apply these ceilings even if the conversation otherwise looks good:

- If a key reasoning step should have used a tool but the assistant mostly solved it from memory or manual explanation, `score` must be at most `4.5`.
- If there is a visible parse error, malformed tool output, invalid JSON/tool-call argument, or similar runtime abnormality, `score` must be at most `4.5`.
- If tool outputs conflict with each other or with the assistant's summary and the assistant does not acknowledge the inconsistency, `score` must be at most `3.5`.
- If the assistant adds unsupported facts, numbers, or interpretations beyond visible evidence, `hallucination_risk` cannot be `none`.
- If the blueprint's key tool actions are not actually pursued in the trajectory, `task_completion_score` should be materially reduced.

### Small deductions

Examples:

- slightly awkward or verbose user turns
- assistant summaries are somewhat loose but still grounded
- mild task design inefficiency
- minor blueprint / trajectory mismatch that does not materially hurt the sample

Typical range: `-0.2` to `-0.8`

### Medium deductions

Examples:

- user sounds synthetic or instructional
- planner goals are weak, unnatural, or only partially reflected in the trajectory
- assistant uses tools clumsily but remains somewhat grounded
- conversation flow is inconsistent but still recoverable

Typical range: `-0.8` to `-1.8`

### Large deductions

Examples:

- assistant contradicts tool outputs
- fabricated facts or numbers
- malformed tool usage that materially damages sample quality
- user behaves nothing like a real user
- blueprint is incoherent, impossible, or badly mismatched to the trajectory

Typical range: `-1.8` to `-4.0`

---

## Hallucination Guidance

Use:

- `none` when the assistant is consistently grounded in visible evidence
- `low` when there are minor ambiguities or slight overreach
- `medium` when there are clear inconsistencies, weak grounding, or visible over-claiming
- `high` when the assistant fabricates, contradicts tool results, or repeatedly misuses tools in ways that corrupt the sample

Do not use `hallucination_risk` as a general bucket for all quality problems.
User or planner problems should primarily lower `score` and `task_completion_score`.

Do not treat superficial tool-name differences as hallucination or planner mismatch.
Penalize only if the assistant uses a materially different tool, fails to pursue the intended action, or makes claims not supported by visible evidence.
Visible runtime noise that weakens trust should still lower `score` even when tool names are semantically equivalent.

---

## Final Reminder

Judge only what is visible in the blueprint and trajectory.

A strong sample should have:

- a coherent task blueprint
- a believable synthetic user
- a grounded and useful assistant
- a trajectory that reflects the intended task
- consistent evidence across turns
- clean, trustworthy tool execution traces

Output only the JSON object.

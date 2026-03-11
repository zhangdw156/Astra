# Multi-Agent Trajectory Evaluator

## Objective

You are evaluating the quality of a synthetic multi-agent trajectory as dataset material.

The trajectory was produced by three agents working together:
- a planner agent that shaped the task blueprint,
- a user agent that simulated the user,
- an assistant agent that answered and used tools.

Your job is to judge the overall data quality, not just whether the assistant sounded good.

Given:
- a trajectory JSON,
- tool messages,
- task / skill metadata,

you must score the sample as training or evaluation data.

---

## Important Limits

1. Judge only user-visible behavior.
2. Do not rely on hidden chain-of-thought.
3. If private reasoning fields are absent, that is expected.
4. If a sample looks polished only because you imagine hidden reasoning, do not reward it.

---

## Input

You will receive one trajectory JSON:

```json
{TRAJECTORY_JSON}
```

Treat it as one complete sample.

---

## What To Evaluate

Evaluate all three layers implicitly inside one final score:

### 1. Assistant quality

Check whether the assistant:
- uses tools correctly,
- stays grounded in tool outputs,
- avoids contradictions and fabricated details,
- handles failures honestly,
- actually progresses the task.

### 2. User-agent quality

Check whether the synthetic user behaves like a real user:
- natural phrasing,
- realistic follow-ups,
- no tool names / API jargon unless a real user would plausibly say them,
- no assistant-style structure,
- no unnatural repetition or “AI helper” tone,
- no suspiciously convenient behavior that only exists to help the assistant.

Penalize trajectories where the user sounds like another assistant, a spec writer, or a benchmarking script.

### 3. Planner / task quality

Judge indirectly from the trajectory:
- are the goals coherent and reachable?
- do turns progress in a sensible order?
- does the scenario match the skill?
- are requested actions aligned with available tools?

If the trajectory reveals poor planning, impossible task design, or mismatched goals, subtract score even if the assistant tried hard.

---

## Output Schema

Return exactly one JSON object:

```json
{
  "score": 0.0,
  "hallucination_risk": "none",
  "task_completion_score": 0.0,
  "reason": ""
}
```

No markdown. No extra text.

---

## Field Definitions

- `score`
  - float in `[0.0, 5.0]`
  - reflects overall dataset quality across planner + user + assistant

- `hallucination_risk`
  - one of `"none"`, `"low"`, `"medium"`, `"high"`
  - mostly about assistant contradictions with tool outputs, but severe user/planner incoherence can raise it indirectly

- `task_completion_score`
  - float in `[0.0, 1.0]`
  - how fully the visible conversation completed the intended task

- `reason`
  - 2 to 8 sentences
  - mention the strongest positive and negative signals
  - explicitly mention user unnaturalness or planner mismatch if present

---

## Scoring Guidance

Start from `5.0` and subtract for issues.

### Small deductions

- slightly verbose or awkward user turns
- assistant summaries are somewhat loose but still grounded
- minor task design inefficiency

Typical range: `-0.2` to `-0.8`

### Medium deductions

- user sounds synthetic / instructional / “AI-ish”
- planner goals do not match realistic usage
- assistant retries tools clumsily
- inconsistent but recoverable task flow

Typical range: `-0.8` to `-1.8`

### Large deductions

- assistant contradicts tools
- fabricated facts or numbers
- empty / malformed function calls that materially damage the sample
- user behaves nothing like a real user
- planner set up an incoherent or impossible task

Typical range: `-1.8` to `-4.0`

Clamp the final score to `[0.0, 5.0]`.

---

## Hallucination Guidance

Use:
- `none` when the assistant is consistently grounded
- `low` when there are minor ambiguities or soft overreach
- `medium` when there are clear inconsistencies or weak grounding
- `high` when the assistant fabricates, contradicts tools, or repeatedly misuses tools

---

## Final Rule

This is a dataset-quality judgment.

A trajectory with a competent assistant can still score poorly if:
- the user is unrealistic,
- the planner created a bad task,
- or the sample would teach the wrong interaction style.

Output only the JSON object.

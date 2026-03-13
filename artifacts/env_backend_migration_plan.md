# Top30 Skill Backend Migration Plan

Before reading or editing this plan, always read:

- [env_top30_backend_notes.md](/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md)

This file is the high-level memory for backend categorization and BFCL analogs. Treat it as required context for every migration session so the implementation does not drift away from the earlier classification.

---

## TODO List

Rule:
- Every time one skill migration is completed, change its checkbox from `[ ]` to `[x]`.
- Completion means: `environment_profile.json`, `backend.py`, at least one scenario, fixture data if needed, and runtime can execute the skill through `ProgramToolExecutor`.
- Before touching any item below, re-read [env_top30_backend_notes.md](/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md).

### Wave 1: direct BFCL-style backends

- [ ] `2466_workspace-files`
- [ ] `3429_unit-convert`
- [ ] `1252_financial-calculator`
- [ ] `5704_memo-persistent-memory`
- [ ] `5403_knowledge-graph`
- [ ] `3986_agent-access-control`
- [ ] `6834_erpclaw-support`
- [ ] `6506_paper-trader`
- [ ] `6621_ninebot-device-skill`
- [ ] `2720_deep-current`

### Wave 2: fixture-backed program backends

- [ ] `1822_code-search`
- [ ] `1823_openclaw-code-search`
- [ ] `1534_voipms-sms`
- [ ] `1939_telnyx`
- [ ] `1141_moltx`
- [ ] `4435_agentx-news`
- [ ] `6734_agentgram`
- [ ] `5938_pager-triage`
- [ ] `6594_linear-issues`
- [ ] `669_stock-strategy-backtester-clean`
- [ ] `6723_flightsearch`
- [ ] `2142_entur-travel`
- [ ] `3581_hackernews`
- [ ] `3220_hackernews-cn`

### Wave 3: hybrid backends

- [ ] `2821_claudemem`
- [ ] `1104_mem0-1-0-0`
- [ ] `2190_qmd-memory`
- [ ] `3677_crypto-self-learning`
- [ ] `5374_kontour-travel-planner`
- [ ] `6287_math-solver`

---

## Objective

Replace the current single-path `tools.jsonl -> ToolAgent -> LLM-generated tool response/state` runtime with a mixed backend architecture:

- strong skills use deterministic local program backends
- open or partially generative skills use hybrid backends
- unmigrated skills can still fall back to the current ToolAgent path

The target design is BFCL-like in the parts that matter:

1. each migrated skill has an executable backend
2. each run loads a deterministic initial scenario
3. tool calls execute against real state
4. final state is programmatically validated
5. tool-response text is no longer the source of truth for migrated skills

---

## Current Constraints From Existing Astra Code

These files define the current flow and therefore constrain the migration design:

- [mcp_runtime.py](/home/zhang/work/Astra/src/astra/simulation/mcp_runtime.py)
- [runner.py](/home/zhang/work/Astra/src/astra/simulation/runner.py)
- [pipeline.py](/home/zhang/work/Astra/src/astra/simulation/pipeline.py)
- [types.py](/home/zhang/work/Astra/src/astra/simulation/types.py)
- [src/astra/agent/_tool_agent/agent.py](/home/zhang/work/Astra/src/astra/agent/_tool_agent/agent.py)
- [src/astra/agent/_planner_agent/agent.py](/home/zhang/work/Astra/src/astra/agent/_planner_agent/agent.py)
- [src/astra/agent/_planner_agent/validator.py](/home/zhang/work/Astra/src/astra/agent/_planner_agent/validator.py)
- [planner_agent.md](/home/zhang/work/Astra/src/astra/prompts/planner_agent.md)
- [tool_agent.md](/home/zhang/work/Astra/src/astra/prompts/tool_agent.md)
- [eval_agent.md](/home/zhang/work/Astra/src/astra/prompts/eval_agent.md)

Important observations:

1. `LocalMCPRuntime` currently owns `ToolAgent` directly and assumes LLM-backed tool execution.
2. `SimulationRunner` only depends on runtime APIs such as `start`, `stop`, `reset_state`, `get_state`, `url`, and tool signature. This means runtime internals can be replaced without rewriting the whole runner.
3. `PlannerAgent` currently only consumes `SKILL.md + tools.jsonl + persona`, so it has no environment awareness.
4. `BlueprintValidator` currently validates only the old schema.
5. `SimulationResult` records `final_tool_state`, but not structured state transitions or initial scenario metadata.

The runtime layer is therefore the critical first refactor, not the planner.

---

## Target Skill Layout

All migrated skills live under:

- [env_top30_skills](/home/zhang/work/Astra/artifacts/env_top30_skills)

Each migrated skill should gradually converge to this flat layout:

```text
artifacts/env_top30_skills/<skill>/
  SKILL.md
  tools.jsonl
  scripts/
  environment_profile.json
  backend.py
  scenarios/
    default.json
  fixtures/
    ...
  tests/
    ...
```

Design rules:

- keep business semantics inside the skill directory
- keep generic runtime, loading, validation, and planner support inside `src/astra`
- never put per-skill business logic into `src/astra`

---

## Backend Contract

Every migrated skill backend should implement one class with the same public protocol.

Suggested contract:

```python
class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict): ...
    def load_scenario(self, scenario: dict) -> None: ...
    def reset(self) -> None: ...
    def call(
        self,
        tool_name: str,
        arguments: dict,
        conversation_context: str | None = None,
    ) -> dict: ...
    def snapshot_state(self) -> dict: ...
    def visible_state(self) -> dict: ...
```

Notes:

- `snapshot_state()` returns full internal state used for validation and artifact writing.
- `visible_state()` is optional but useful when only part of internal state should reach prompts or artifacts.
- `call(...)` returns a JSON-serializable dict; for migrated skills, this is the canonical tool result.
- hybrid backends may internally call LLMs for derived text, but state mutation must still be programmatic.

---

## `environment_profile.json` Schema

Every migrated skill gets one profile file.

Suggested minimum structure:

```json
{
  "backend_mode": "program-direct",
  "state_mode": "json",
  "validation_mode": "final_state",
  "scenario_source": "inline",
  "bfcl_analog": "ticket_api",
  "entry_class": "SkillBackend",
  "tool_names": ["add_issue", "get_issue", "update_issue"],
  "default_scenario": "default",
  "notes_ref": "/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md"
}
```

Allowed values:

- `backend_mode`: `program-direct` | `program-fixture` | `hybrid` | `llm-fallback`
- `state_mode`: `stateless` | `json` | `sqlite`
- `validation_mode`: `none` | `final_state` | `turn_state`
- `scenario_source`: `inline` | `fixture`

The `notes_ref` field must point at [env_top30_backend_notes.md](/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md) so every skill-level artifact can keep that dependency explicit.

---

## `mcp_runtime` Redesign

This is the most important engineering change.

### Current problem

[mcp_runtime.py](/home/zhang/work/Astra/src/astra/simulation/mcp_runtime.py) directly creates `ToolAgent`, loads `tools.jsonl`, and registers LLM handlers into FastMCP. This hard-wires runtime and backend execution together.

### Target architecture

Keep one runtime abstraction, but make execution pluggable.

```text
LocalMCPRuntime
  -> ToolRegistry
  -> ToolExecutor
       -> LLMToolExecutor
       -> ProgramToolExecutor
```

### Runtime responsibilities after refactor

- start and stop FastMCP
- load tool schemas
- register tool handlers
- route each MCP tool call into a chosen executor
- expose state for `SimulationRunner`
- persist state transition metadata

### Executor responsibilities

- `LLMToolExecutor`
  - wraps current `ToolAgent.generate_response`
  - remains fallback for unmigrated skills
- `ProgramToolExecutor`
  - loads `environment_profile.json`, `backend.py`, and scenario
  - executes real backend method
  - returns canonical result + state snapshot

### Required runtime behavior changes

1. `reset_state` for program backends must call `backend.reset()` and then reload scenario.
2. `get_state` for program backends must return `backend.snapshot_state()`, not an LLM state store.
3. each tool call should capture:
   - `before_state`
   - `after_state`
   - `tool_name`
   - `arguments`
   - `result`
4. if a skill has no environment profile, runtime falls back to the existing LLM path.

---

## `src/astra` File-by-File Plan

## New files

### 1. `src/astra/envs/base.py`

Purpose:
- define backend protocol / abstract base

Key contents:
- `SkillBackendProtocol`
- `BackendExecutionResult`
- helper type aliases for `StateDict`, `ToolArguments`

### 2. `src/astra/envs/types.py`

Purpose:
- structured dataclasses for environment profile and scenario metadata

Suggested classes:
- `EnvironmentProfile`
- `ScenarioSpec`
- `StateTransitionRecord`

### 3. `src/astra/envs/loader.py`

Purpose:
- load skill backend files from a skill directory

Responsibilities:
- parse `environment_profile.json`
- import `backend.py`
- instantiate backend class
- locate `scenarios/default.json`

### 4. `src/astra/envs/validation.py`

Purpose:
- compare actual final state with expected final state
- compare checkpoint state slices

Responsibilities:
- dict/list deep comparison with optional subset matching
- machine-friendly diff output

### 5. `src/astra/simulation/tool_registry.py`

Purpose:
- move `tools.jsonl` loading and MCP registration out of `ToolAgent`

Responsibilities:
- load tool schemas
- build tool-name signature
- register generic handler for each tool

### 6. `src/astra/simulation/executors/base.py`

Purpose:
- `ToolExecutor` protocol

### 7. `src/astra/simulation/executors/llm_executor.py`

Purpose:
- adapter around current `ToolAgent`

### 8. `src/astra/simulation/executors/program_executor.py`

Purpose:
- program backend execution path

Responsibilities:
- load backend from skill dir
- load default or blueprint-specified scenario
- dispatch tool calls
- expose canonical state snapshots

### 9. `src/astra/simulation/environment_context.py`

Purpose:
- central helper for passing environment metadata into planner, runner, and eval

Responsibilities:
- serialize profile summary for prompts
- expose scenario choices

---

## Existing files to modify

### 10. `src/astra/simulation/mcp_runtime.py`

Change:
- stop directly owning `ToolAgent`
- accept executor + registry abstraction

Required interface changes:
- constructor should accept `skill_dir` in addition to `tools_path`
- runtime should detect whether a program backend exists
- runtime should keep `state_transitions`

### 11. `src/astra/simulation/runner.py`

Change:
- `build_runtime(...)` must pass `skill_dir`
- trajectory result should include:
  - `initial_state`
  - `scenario_id`
  - `state_transitions`
  - `environment_profile`

Validation changes:
- if blueprint provides `expected_final_state`, compare with runtime final state programmatically
- if blueprint provides checkpoints, validate per turn

### 12. `src/astra/simulation/types.py`

Change:
- expand `SimulationTurn`
- expand `SimulationResult`

Add fields:
- `initial_state`
- `scenario_id`
- `environment_profile`
- `state_transitions`
- per-tool-call `before_state` / `after_state` summaries

### 13. `src/astra/simulation/pipeline.py`

Change:
- `run_sample(...)` and `run_batch(...)` should pass `skill_dir` through to runtime-building code
- persist new blueprint/runtime artifacts cleanly

### 14. `src/astra/agent/_tool_agent/agent.py`

Change:
- shrink responsibility
- keep only the LLM execution path

Split out:
- tools schema loading
- MCP registration

### 15. `src/astra/agent/_tool_agent/types.py`

Change:
- add richer execution envelope if LLM executor remains in use

### 16. `src/astra/agent/_planner_agent/types.py`

Change:
- `PlannerRunContext` should include:
  - `environment_profile_path`
  - `scenario_dir`
  - optional loaded profile summary

### 17. `src/astra/agent/_planner_agent/prompt_builder.py`

Change:
- support new placeholders:
  - `{ENVIRONMENT_PROFILE}`
  - `{SCENARIO_SUMMARY}`

### 18. `src/astra/agent/_planner_agent/agent.py`

Change:
- load `environment_profile.json` if present
- generate environment-aware blueprint
- inject `scenario_id`, `environment_profile`, `initial_state`, `expected_final_state`

### 19. `src/astra/agent/_planner_agent/validator.py`

Change:
- validate blueprint v2 fields

New required or optional fields:
- `scenario_id`
- `environment_profile`
- `state_checkpoints`
- stronger rules for `initial_state` / `expected_final_state`

### 20. `src/astra/agent/_eval_agent/prompt_builder.py`

Change:
- include environment profile and final state diff summary in eval prompt input

### 21. `src/astra/agent/_eval_agent/agent.py`

Change:
- feed state diff / completion stats into the eval prompt

### 22. `src/astra/agent/_eval_agent/types.py`

Change:
- add optional machine-derived completion diagnostics

---

## Prompt Files To Modify

### 23. `src/astra/prompts/planner_agent.md`

Current problem:
- no concept of environment profile or scenario

Required changes:
- add new input section for:
  - `environment_profile.json`
  - scenario summary
- require blueprint output to include:
  - `scenario_id`
  - `initial_state`
  - `expected_final_state`
  - optional `state_checkpoints`
  - `environment_profile`
- tell planner to avoid inventing execution-time facts but to define structural target state

### 24. `src/astra/prompts/user_agent.md`

Current problem:
- user only follows ordered goals

Required changes:
- add awareness that some goals depend on already-initialized environment state
- tell user agent to remain consistent with any already-known state surfaced by assistant
- no need to expose tool or backend details

This is a prompt tweak, not a role rewrite.

### 25. `src/astra/prompts/tool_agent.md`

Current problem:
- assumes it is the universal tool simulator

Required changes:
- narrow its scope to LLM fallback and hybrid text-generation duties
- explicitly state it must not be used as canonical truth when program state exists

### 26. `src/astra/prompts/eval_agent.md`

Current problem:
- evaluates mostly from blueprint and visible trajectory text

Required changes:
- add machine-generated state-completion context
- prioritize state correctness over stylistic fluency for migrated skills

---

## Blueprint v2 Schema

For migrated skills, planner should produce:

```json
{
  "goals": ["..."],
  "possible_tool_calls": [["..."]],
  "scenario_id": "default",
  "environment_profile": {
    "backend_mode": "program-direct",
    "validation_mode": "final_state"
  },
  "initial_state": {},
  "expected_final_state": {},
  "state_checkpoints": [],
  "user_agent_config": {
    "role": "",
    "personality": "",
    "knowledge_boundary": ""
  },
  "end_condition": ""
}
```

Compatibility rule:
- if a skill has no environment profile, planner can still emit the old schema and the runtime can stay on LLM fallback

---

## Artifact Expectations For Migrated Trajectories

Trajectory artifacts should include at minimum:

- `run_id`
- `trajectory_id`
- `skill_name`
- `scenario_id`
- `environment_profile`
- `initial_state`
- `final_tool_state`
- `state_transitions`
- `structured_turns`
- `validation`

Each tool call inside a turn should ideally include:

- `name`
- `arguments`
- `result`
- `before_state_summary`
- `after_state_summary`

---

## Skill-by-Skill Migration Plan

Every skill entry below assumes:

1. always re-read [env_top30_backend_notes.md](/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md)
2. create `environment_profile.json`
3. create `backend.py`
4. create `scenarios/default.json`
5. create `fixtures/` if needed
6. add minimal local tests where feasible

### `2466_workspace-files`

- backend mode: `program-direct`
- BFCL analog: `gorilla_file_system`
- backend state:
  - sandbox root
  - file tree
- actions:
  - reimplement list/read/write/search as backend methods
  - eliminate dependence on hard-coded user-specific root in shell script
  - create 2 to 3 fixture sandboxes

### `3429_unit-convert`

- backend mode: `program-direct`
- BFCL analog: `math_api`
- backend state: stateless
- actions:
  - move conversion tables into `backend.py`
  - preserve categories/unit listing

### `1252_financial-calculator`

- backend mode: `program-direct`
- BFCL analog: `math_api`
- backend state: stateless
- actions:
  - implement formula methods directly
  - if tables are returned, keep deterministic ordering

### `5704_memo-persistent-memory`

- backend mode: `program-direct`
- BFCL analog: `memory_kv`
- backend state:
  - observations
  - ids
  - tags/created_at if needed
- actions:
  - replace worker-service assumption with local in-process store
  - implement search/get/delete/stats/timeline

### `5403_knowledge-graph`

- backend mode: `program-direct`
- BFCL analog: `memory_kv`
- backend state:
  - entities
  - fact list
  - superseded links
  - summary cache
- actions:
  - port file-based JSON logic into backend class
  - summary generation can remain deterministic templating

### `3986_agent-access-control`

- backend mode: `program-direct`
- BFCL analog: `message_api`
- backend state:
  - ownerIds
  - approvedContacts
  - pendingApprovals
  - blockedIds
  - rateLimits
- actions:
  - initialize from existing JSON schema
  - implement all contact approval/rate-limit transitions programmatically

### `6834_erpclaw-support`

- backend mode: `program-direct`
- BFCL analog: `ticket_api`
- backend state:
  - SQLite fixture or in-memory relational clone
  - issues/comments/SLA/customer/company records
- actions:
  - wrap existing DB logic as backend methods
  - freeze a compact sample DB inside `fixtures/`

### `6506_paper-trader`

- backend mode: `program-direct`
- BFCL analog: `trading_bot`
- backend state:
  - accounts
  - events
  - positions
  - price snapshots
- actions:
  - move DB path control into backend instance
  - make each scenario a seeded account state

### `6621_ninebot-device-skill`

- backend mode: `program-direct`
- BFCL analog: `vehicle_control`
- backend state:
  - auth token
  - device list
  - per-device status
- actions:
  - formalize current `--mock` data as scenario-backed state
  - avoid live HTTP in migrated mode

### `2720_deep-current`

- backend mode: `program-direct`
- BFCL analog: `memory_kv` + `web_search`
- backend state:
  - threads
  - notes
  - sources
  - findings
  - status
- actions:
  - port JSON file logic into backend class
  - keep research-thread state canonical

### `1822_code-search`

- backend mode: `program-fixture`
- BFCL analog: `gorilla_file_system`
- actions:
  - create small frozen codebase fixtures
  - backend methods map to `grep/glob/tree/check`

### `1823_openclaw-code-search`

- backend mode: `program-fixture`
- same plan as `1822_code-search`

### `1534_voipms-sms`

- backend mode: `program-fixture`
- BFCL analog: `message_api`
- backend state:
  - inbox/outbox/messages/contact ids

### `1939_telnyx`

- backend mode: `program-fixture`
- BFCL analog: `message_api`
- backend state:
  - messages
  - calls
  - numbers
  - call lifecycle

### `1141_moltx`

- backend mode: `program-fixture`
- BFCL analog: `posting_api`
- backend state:
  - agent profile
  - posts
  - mentions
  - notifications
  - following feed

### `4435_agentx-news`

- backend mode: `program-fixture`
- BFCL analog: `posting_api`
- backend state:
  - agents
  - xeets
  - follows
  - blocks
  - timeline

### `6734_agentgram`

- backend mode: `program-fixture`
- BFCL analog: `posting_api`
- backend state:
  - auth
  - profile
  - posts
  - likes
  - follows
  - comments

### `5938_pager-triage`

- backend mode: `program-fixture`
- BFCL analog: `ticket_api`
- backend state:
  - incidents
  - services
  - oncall roster
  - notes
  - ack/resolve status

### `6594_linear-issues`

- backend mode: `program-fixture`
- BFCL analog: `ticket_api`
- backend state:
  - teams
  - users
  - issues
  - comments
  - states

### `669_stock-strategy-backtester-clean`

- backend mode: `program-fixture`
- BFCL analog: read-only trading backend
- backend state:
  - fixture csv catalog
  - last run metadata
- actions:
  - keep results deterministic per csv + strategy args

### `6723_flightsearch`

- backend mode: `program-fixture`
- BFCL analog: `travel_booking`
- backend state:
  - flights by route/date
  - recommendation results
- actions:
  - remove live HTTP from migrated path

### `2142_entur-travel`

- backend mode: `program-fixture`
- BFCL analog: `travel_booking`
- backend state:
  - stops
  - trips
  - departures

### `3581_hackernews`

- backend mode: `program-fixture`
- BFCL analog: `web_search`
- backend state:
  - frozen HN stories/comments/users

### `3220_hackernews-cn`

- backend mode: `program-fixture`
- BFCL analog: `web_search`
- backend state:
  - frozen HN/Algolia-like result sets

### `2821_claudemem`

- backend mode: `hybrid`
- backend state:
  - notes
  - sessions
  - search index metadata
- actions:
  - memory transitions programmatic
  - export/summary fields may be templated

### `1104_mem0-1-0-0`

- backend mode: `hybrid`
- BFCL analog: `memory_vector`
- backend state:
  - memory entries
  - fake embeddings or deterministic vector placeholders
- actions:
  - no external OpenAI/vector DB in migrated mode

### `2190_qmd-memory`

- backend mode: `hybrid`
- backend state:
  - collections
  - contexts
  - templates
  - search metadata

### `3677_crypto-self-learning`

- backend mode: `hybrid`
- BFCL analog: trading + memory
- backend state:
  - trades
  - learned rules
  - memory entries
- actions:
  - `log_trade` and `update_memory` programmatic
  - `generate_rules` constrained templating or limited LLM

### `5374_kontour-travel-planner`

- backend mode: `hybrid`
- backend state:
  - trip draft
  - slots: dates/budget/travelers/interests
  - completeness flags
- actions:
  - planner state transitions programmatic
  - narrative plan output templated

### `6287_math-solver`

- backend mode: `hybrid`
- actions:
  - programmatic support for `convert`, `formula`, maybe `graph` metadata
  - keep open-ended explanation tools as fallback or templated text
- note:
  - lowest backend payoff among the 30

---

## Implementation Waves

### Wave A: framework first

Do not migrate more skills before this framework layer exists.

1. add `src/astra/envs/*`
2. add executor abstractions
3. refactor `mcp_runtime.py`
4. preserve LLM fallback
5. extend trajectory schema

### Wave B: strongest skill backends

Implement in this order:

1. `2466_workspace-files`
2. `3429_unit-convert`
3. `5704_memo-persistent-memory`
4. `6506_paper-trader`
5. `6834_erpclaw-support`

These five are enough to prove the architecture.

### Wave C: planner and eval awareness

1. upgrade blueprint schema
2. modify planner prompt, types, validator
3. inject environment profile and scenario summary
4. add programmatic final-state validation to runner/eval

### Wave D: remaining program-direct and program-fixture skills

Migrate the rest of wave 1 and wave 2.

### Wave E: hybrid skills

Handle only after the direct backends are stable.

---

## Definition of Done Per Skill

A skill is complete only when all are true:

1. `environment_profile.json` exists
2. `backend.py` exists and loads
3. `scenarios/default.json` exists
4. runtime executes tool calls through `ProgramToolExecutor`
5. `final_tool_state` is produced by backend state, not ToolAgent state
6. at least one blueprint can include `scenario_id` and `expected_final_state`
7. the checklist item at the top of this file is flipped to `[x]`

---

## Session Discipline

For every future migration session:

1. read [env_top30_backend_notes.md](/home/zhang/work/Astra/artifacts/env_top30_backend_notes.md)
2. read this plan
3. work only inside [env_top30_skills](/home/zhang/work/Astra/artifacts/env_top30_skills) for skill-local backend logic
4. keep generic framework changes inside `src/astra`
5. when one skill is complete, immediately update the TODO checkbox in this file

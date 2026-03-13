# Top 30 Skill Backend Notes

Working copy root: `/home/zhang/work/Astra/artifacts/env_top30_skills`

Reference BFCL backend patterns:
- `gorilla_file_system.py`: sandboxed read/write file environment
- `math_api.py`: stateless deterministic compute tools
- `memory_kv.py` / `memory_vector.py`: persistent memory with snapshot restore
- `message_api.py` / `posting_api.py`: account/message/feed state machines
- `ticket_api.py`: ticket queue with CRUD + status transitions
- `trading_bot.py`: portfolio / orders / positions state machine
- `travel_booking.py`: booking state + auth + payment + inventory
- `vehicle_control.py`: device auth + device state query
- `web_search.py`: search/fetch wrapper, can stay external or be fixture-backed

Recommended backend modes:
- `program-direct`: implement as deterministic Python backend with explicit state
- `program-fixture`: implement as deterministic backend over local fixtures / seeded data
- `hybrid`: program state transitions + optional LLM/text synthesis for open-ended fields
- `llm-last`: keep current ToolAgent path for now; low payoff or too open-ended

## Per-skill recommendations

| Skill | Domain | BFCL analog | Recommended mode | Initial state / notes |
|---|---|---|---|---|
| `1823_openclaw-code-search` | file system | `gorilla_file_system.py` | `program-fixture` | Seed a sandbox tree; expose `grep/glob/tree/check`; mostly read-only. |
| `2466_workspace-files` | file system | `gorilla_file_system.py` | `program-direct` | Seed workspace root and file contents; state is filesystem snapshot after writes. |
| `1822_code-search` | file system | `gorilla_file_system.py` | `program-fixture` | Same as above; can share one backend with different fixture bundles. |
| `3429_unit-convert` | math | `math_api.py` | `program-direct` | Stateless conversion table backend. |
| `1252_financial-calculator` | math | `math_api.py` | `program-direct` | Stateless formulas for FV/PV/discount/markup/tables. |
| `6287_math-solver` | math | none exact; closer to tutor prompt wrapper | `llm-last` | `solve/step/graph/formula/practice` are mostly prompt templates, not environment state. Keep lightweight for now. |
| `5704_memo-persistent-memory` | memory kv | `memory_kv.py` | `program-direct` | SQLite/FTS-like memory store; snapshotable observations and ids. Strong BFCL candidate. |
| `5403_knowledge-graph` | memory kv | `memory_kv.py` | `program-direct` | Seed entity/fact graph; state is entities, facts, superseded links, summaries. |
| `2821_claudemem` | memory kv | `memory_kv.py` | `hybrid` | Likely memory management is programmatic, but some summarization/export behavior may be looser. |
| `1104_mem0-1-0-0` | memory vector | `memory_vector.py` | `hybrid` | Replace external embedder/vector store with local mock vector index + deterministic similarity. |
| `2190_qmd-memory` | memory vector | `memory_vector.py` | `hybrid` | Needs local collection/context state; serve/search can be fixture-backed, but templates may need text generation. |
| `3986_agent-access-control` | message api | `message_api.py` | `program-direct` | JSON state machine: owners, approved contacts, pending approvals, rate limits, notify targets. |
| `1534_voipms-sms` | message api | `message_api.py` | `program-fixture` | Model inbox/outbox, contacts, message ids, delivery status; no real API needed. |
| `1939_telnyx` | message api | `message_api.py` | `program-fixture` | Add numbers, calls, messages, call status transitions. High payoff, but more schema work. |
| `1141_moltx` | posting api | `posting_api.py` | `program-fixture` | Feed/profile/mentions/notifications can be local social graph fixtures. |
| `4435_agentx-news` | posting api | `posting_api.py` | `program-fixture` | Same social-state pattern: agents, xeets, follows, blocks, timeline. |
| `6734_agentgram` | posting api | `posting_api.py` | `program-fixture` | Very good fit for BFCL-style posting backend: register/me/status/feed/comments/likes/follows. |
| `6834_erpclaw-support` | ticket api | `ticket_api.py` | `program-direct` | Strongest ticket candidate. Already SQLite-backed with issue/SLA/comment workflows. |
| `5938_pager-triage` | ticket api | `ticket_api.py` | `program-fixture` | Normalize incidents/oncall/services/ack/resolve/note into a seeded incident queue backend. |
| `6594_linear-issues` | ticket api | `ticket_api.py` | `program-fixture` | Seed teams/users/issues/states/comments. Local Linear clone backend is straightforward. |
| `669_stock-strategy-backtester-clean` | trading bot | `trading_bot.py` (read-only variant) | `program-fixture` | Deterministic over local CSV fixtures; state can just record last run inputs/outputs. |
| `3677_crypto-self-learning` | trading bot | `trading_bot.py` + memory | `hybrid` | `log_trade` and memory updates are programmatic; `generate_rules` is open-ended and should be constrained or templated. |
| `6506_paper-trader` | trading bot | `trading_bot.py` | `program-direct` | Strong BFCL candidate: account, positions, snapshots, levels, notes, realized PnL. |
| `6723_flightsearch` | travel booking | `travel_booking.py` (search-only slice) | `program-fixture` | Replace external HTTP with local flight search fixture by city/date/user. |
| `2142_entur-travel` | travel booking | `travel_booking.py` | `program-fixture` | Seed stops, departures, trips. Read-heavy with little mutation. |
| `5374_kontour-travel-planner` | travel booking | none exact; planning state machine | `program-direct` | Conversation/planning state can be modeled as trip draft JSON with completeness stages. |
| `6621_ninebot-device-skill` | vehicle control | `vehicle_control.py` | `program-direct` | Use existing `--mock` semantics: auth token, device list, per-device status/location/battery. |
| `2720_deep-current` | web search + memory | `memory_kv.py` / `web_search.py` | `program-direct` | Thread manager itself is local JSON state; keep external search separate from thread state. |
| `3581_hackernews` | web search | `web_search.py` | `program-fixture` | Use frozen HN fixture snapshots for top/new/item/comments/user. |
| `3220_hackernews-cn` | web search | `web_search.py` | `program-fixture` | Same as above; local fixture snapshot for stories/search results. |

## Grouping by engineering payoff

### Best first-wave BFCL-style backends

These have clear state, deterministic semantics, and high validation payoff:

1. `2466_workspace-files`
2. `3429_unit-convert`
3. `1252_financial-calculator`
4. `5704_memo-persistent-memory`
5. `5403_knowledge-graph`
6. `3986_agent-access-control`
7. `6834_erpclaw-support`
8. `6506_paper-trader`
9. `6621_ninebot-device-skill`
10. `2720_deep-current`

### Good second wave with local fixture datasets

1. `1822_code-search`
2. `1823_openclaw-code-search`
3. `1534_voipms-sms`
4. `1939_telnyx`
5. `1141_moltx`
6. `4435_agentx-news`
7. `6734_agentgram`
8. `5938_pager-triage`
9. `6594_linear-issues`
10. `669_stock-strategy-backtester-clean`
11. `6723_flightsearch`
12. `2142_entur-travel`
13. `3581_hackernews`
14. `3220_hackernews-cn`

### Keep hybrid or LLM-backed until later

1. `6287_math-solver`
2. `2821_claudemem`
3. `1104_mem0-1-0-0`
4. `2190_qmd-memory`
5. `3677_crypto-self-learning`
6. `5374_kontour-travel-planner`

## Recommended environment contracts

For `program-*` backends, add per-skill files like:

- `environment_profile.json`
- `scenarios/default_initial_state.json`
- `backend.py`
- `fixtures/...`

Suggested `environment_profile.json` fields:

```json
{
  "backend_mode": "program-direct",
  "state_mode": "json",
  "validation_mode": "final_state",
  "scenario_source": "fixture",
  "bfcl_analog": "ticket_api",
  "tool_names": ["add_issue", "update_issue", "get_issue"]
}
```

Suggested blueprint additions once these backends exist:

- `scenario_id`
- `initial_state`
- `expected_final_state`
- `state_checkpoints`
- `validation_mode`

## Design guidance borrowed from BFCL

1. Keep one backend class per skill or per domain cluster, not one handler per tool.
2. Load deterministic `initial_state` before every run, similar to BFCL `_load_scenario(...)`.
3. Prefer class attributes / JSON snapshot / SQLite file as the source of truth.
4. Compare end state against `expected_final_state`; add turn-level checks only for the strongest environments.
5. For search-style tools, freeze response fixtures instead of calling the live network.
6. For hybrid tools, keep state transitions programmatic and limit LLM use to derived text fields only.

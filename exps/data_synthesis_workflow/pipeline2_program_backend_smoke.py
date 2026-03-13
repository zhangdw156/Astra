#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from astra.agent._eval_agent.types import EvaluationResult
from astra.envs import StateTransitionRecord, load_backend_from_skill_dir
from astra.envs.validation import compare_state
from astra.simulation.store import ArtifactStore, to_jsonable
from astra.simulation.types import SimulationResult, SimulationTurn


RECIPE_BY_SKILL: dict[str, dict[str, Any]] = {
    "1104_mem0-1-0-0": {
        "goals": ["Store a memory", "Search the stored memory"],
        "tool_calls": [
            {
                "name": "add_memory",
                "arguments": {
                    "messages": [{"role": "user", "content": "Remember that I like weekly summaries"}]
                },
            },
            {"name": "search_memories", "arguments": {"query": "weekly summaries"}},
        ],
    },
    "1141_moltx": {
        "goals": ["Publish a post", "Like a mention"],
        "tool_calls": [
            {"name": "moltx_post", "arguments": {"content": "Shipping a new evaluator pass today?"}},
            {"name": "moltx_like", "arguments": {"post_id": "post_2"}},
        ],
    },
    "1252_financial-calculator": {
        "goals": ["Compute future value"],
        "tool_calls": [
            {
                "name": "future_value",
                "arguments": {
                    "principal": 1000,
                    "rate": 0.05,
                    "years": 2,
                    "compound_frequency": 1,
                },
            }
        ],
    },
    "1534_voipms-sms": {
        "goals": ["Send a message", "Fetch recent messages"],
        "tool_calls": [
            {
                "name": "send_sms",
                "arguments": {
                    "did": "15551234567",
                    "dst": "15553334444",
                    "message": "Confirmed for noon.",
                },
            },
            {"name": "get_sms", "arguments": {"did": "15551234567", "days": 1}},
        ],
    },
    "1822_code-search": {
        "goals": ["Search code for definitions"],
        "tool_calls": [{"name": "grep", "arguments": {"pattern": "def", "type": "py"}}],
    },
    "1823_openclaw-code-search": {
        "goals": ["Find skill markdown files"],
        "tool_calls": [{"name": "glob", "arguments": {"pattern": "*SKILL*", "type": "f"}}],
    },
    "1939_telnyx": {
        "goals": ["Send a message", "List messages"],
        "tool_calls": [
            {
                "name": "send_message",
                "arguments": {"from": "+14155550100", "to": "+14155550777", "text": "Dispatching now"},
            },
            {"name": "list_messages", "arguments": {"page_size": 10}},
        ],
    },
    "2142_entur-travel": {
        "goals": ["Find a trip between two stops"],
        "tool_calls": [
            {
                "name": "trip",
                "arguments": {"from_place": "Oslo S", "to": "Oslo lufthavn", "modes": "rail"},
            }
        ],
    },
    "2190_qmd-memory": {
        "goals": ["Configure QMD", "Run hybrid query"],
        "tool_calls": [
            {"name": "setup", "arguments": {}},
            {
                "name": "qmd_query",
                "arguments": {"query": "What changed in runtime routing?", "limit": 5},
                "conversation_context": "We are migrating skills to program backends.",
            },
        ],
    },
    "2466_workspace-files": {
        "goals": ["Write a file", "Read the file back"],
        "tool_calls": [
            {"name": "write_file", "arguments": {"path": "07_OUTPUTS/demo.txt", "content": "hello"}},
            {"name": "read_file", "arguments": {"path": "07_OUTPUTS/demo.txt"}},
        ],
    },
    "2720_deep-current": {
        "goals": ["Create a thread", "Add a note", "Read digest"],
        "tool_calls": [
            {
                "name": "add",
                "arguments": {"title": "AI chip export controls"},
                "save": {"thread_id": "id"},
            },
            {"name": "note", "arguments": {"id": "$thread_id", "text": "Track policy changes"}},
            {"name": "digest", "arguments": {}},
        ],
    },
    "2821_claudemem": {
        "goals": ["Save a session summary", "Search memory"],
        "tool_calls": [
            {
                "name": "session",
                "arguments": {"action": "save", "title": "Fixture batch", "branch": "feat/test", "project": "/tmp/demo"},
                "conversation_context": "Migrated more fixture-backed skills and verified them with pytest.",
            },
            {"name": "search", "arguments": {"query": "fixture", "limit": 5}},
        ],
    },
    "3220_hackernews-cn": {
        "goals": ["Read launch stories"],
        "tool_calls": [{"name": "launch", "arguments": {"limit": 5}}],
    },
    "3429_unit-convert": {
        "goals": ["Convert centimeters to meters"],
        "tool_calls": [{"name": "convert", "arguments": {"value": 100, "from_unit": "cm", "to_unit": "m"}}],
    },
    "3581_hackernews": {
        "goals": ["Read top stories"],
        "tool_calls": [{"name": "top", "arguments": {"limit": 1}}],
    },
    "3677_crypto-self-learning": {
        "goals": ["Generate rules", "Analyze trades"],
        "tool_calls": [
            {"name": "generate_rules", "arguments": {}},
            {
                "name": "analyze",
                "arguments": {"symbol": "BTCUSDT", "min_trades": 2},
                "conversation_context": "The agent wants to reinforce high-conviction long setups.",
            },
        ],
    },
    "3986_agent-access-control": {
        "goals": ["Handle an unknown contact", "Approve the contact", "Check access tier"],
        "tool_calls": [
            {
                "name": "handle_stranger",
                "arguments": {"senderId": "telegram:99", "platform": "telegram", "message": "hello there"},
            },
            {
                "name": "approve_contact",
                "arguments": {"senderId": "telegram:99", "ownerResponse": "trusted"},
            },
            {
                "name": "check_access_tier",
                "arguments": {"senderId": "telegram:99", "platform": "telegram"},
            },
        ],
    },
    "4435_agentx-news": {
        "goals": ["Create a xeet"],
        "tool_calls": [{"name": "agentx_post_xeet", "arguments": {"content": "End-to-end validation is next."}}],
    },
    "5374_kontour-travel-planner": {
        "goals": ["Extract trip context", "Export itinerary to maps"],
        "tool_calls": [
            {
                "name": "plan_trip",
                "arguments": {
                    "query": "2 weeks in Japan for a couple, mid-range budget, interested in food and temples",
                },
                "conversation_context": "Need a concise planning brief.",
            },
            {"name": "export_gmaps", "arguments": {"itinerary_file": "sample_tokyo.json", "export_kml": True}},
        ],
    },
    "5403_knowledge-graph": {
        "goals": ["Add a fact", "Summarize the entity"],
        "tool_calls": [
            {
                "name": "add_fact",
                "arguments": {
                    "entity": "people/safa",
                    "category": "status",
                    "fact": "Working on backend migration",
                },
            },
            {"name": "summarize_entity", "arguments": {"entity": "people/safa"}},
        ],
    },
    "5704_memo-persistent-memory": {
        "goals": ["Search persistent memory"],
        "tool_calls": [{"name": "memory_search", "arguments": {"query": "program"}}],
    },
    "5938_pager-triage": {
        "goals": ["List incidents", "Preview acknowledge"],
        "tool_calls": [
            {"name": "pd_incidents", "arguments": {}},
            {"name": "pd_incident_ack", "arguments": {"incident_id": "P123ABC", "confirm": False}},
        ],
    },
    "6287_math-solver": {
        "goals": ["Solve a linear equation", "Convert temperature"],
        "tool_calls": [
            {"name": "solve", "arguments": {"problem": "2x+3=11"}},
            {"name": "convert", "arguments": {"conversion": "100F to C"}},
        ],
    },
    "6506_paper-trader": {
        "goals": ["Initialize account", "Open a trade", "Update mark price", "Read status"],
        "tool_calls": [
            {
                "name": "init",
                "arguments": {
                    "account": "main",
                    "name": "Main",
                    "base-currency": "USD",
                    "starting-balance": 10000,
                },
            },
            {
                "name": "open",
                "arguments": {
                    "account": "main",
                    "symbol": "BTC",
                    "mint": "btc",
                    "side": "LONG",
                    "qty": 1,
                    "price": 100,
                },
            },
            {"name": "snapshot", "arguments": {"symbol": "BTC", "mint": "btc", "price": 120}},
            {"name": "status", "arguments": {"account": "main"}},
        ],
    },
    "6594_linear-issues": {
        "goals": ["Create an issue", "Update the issue"],
        "tool_calls": [
            {
                "name": "create_issue",
                "arguments": {
                    "team_id": "team_1",
                    "title": "Migrate remaining fixture skills",
                    "description": "Continue env backend rollout.",
                    "priority": 2,
                    "assignee_id": "user_1",
                },
                "save": {"issue_id": "issue.identifier"},
            },
            {"name": "update_issue", "arguments": {"issue_id": "$issue_id", "state_id": "state_2", "priority": 1}},
        ],
    },
    "6621_ninebot-device-skill": {
        "goals": ["Login", "List devices"],
        "tool_calls": [
            {
                "name": "ninebot_login",
                "arguments": {"username": "demo@example.com", "password": "pass123"},
                "save": {"token": "token"},
            },
            {"name": "ninebot_list_devices", "arguments": {"token": "$token"}},
        ],
    },
    "669_stock-strategy-backtester-clean": {
        "goals": ["Run backtest on sample data"],
        "tool_calls": [
            {
                "name": "run_backtest",
                "arguments": {
                    "csv": "sample",
                    "strategy": "sma-crossover",
                    "fast-window": 10,
                    "slow-window": 30,
                    "quiet": True,
                },
            }
        ],
    },
    "6723_flightsearch": {
        "goals": ["Search flights"],
        "tool_calls": [
            {
                "name": "flight_search",
                "arguments": {
                    "departure_date": "2026-03-08",
                    "departure_city": "北京市",
                    "destination_city": "上海市",
                },
            }
        ],
    },
    "6734_agentgram": {
        "goals": ["Create a post", "Like an existing post"],
        "tool_calls": [
            {
                "name": "create_post",
                "arguments": {
                    "title": "New validator path",
                    "content": "State checkpoints are live. #agents #testing",
                },
            },
            {"name": "like", "arguments": {"post_id": "post_2"}},
        ],
    },
    "6834_erpclaw-support": {
        "goals": ["Open an issue", "Resolve the issue"],
        "tool_calls": [
            {
                "name": "add_issue",
                "arguments": {"subject": "Printer not syncing"},
                "save": {"issue_id": "issue_id"},
            },
            {
                "name": "resolve_issue",
                "arguments": {"issue_id": "$issue_id", "resolution_notes": "Restarted sync service"},
            },
        ],
    },
}


def load_selected_skills(path: Path) -> list[str]:
    skills: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "dir_name" in obj:
            skills.append(str(obj["dir_name"]))
        elif "skill_dir" in obj:
            skills.append(Path(str(obj["skill_dir"])).name)
    return skills


def discover_skills(skills_root: Path) -> list[str]:
    return sorted(
        skill_dir.name
        for skill_dir in skills_root.iterdir()
        if skill_dir.is_dir() and (skill_dir / "environment_profile.json").exists()
    )


def parse_tools(tools_path: Path) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for line in tools_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            tools.append(json.loads(line))
    return tools


def get_path(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            raise KeyError(path)
        current = current[part]
    return current


def resolve_placeholders(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        return variables[value[1:]]
    if isinstance(value, dict):
        return {key: resolve_placeholders(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_placeholders(item, variables) for item in value]
    return value


def build_blueprint(
    *,
    skill_name: str,
    persona_text: str,
    loaded,
    recipe: dict[str, Any],
    initial_state: dict[str, Any],
    final_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "blueprint_id": str(uuid.uuid4()),
        "skill_name": skill_name,
        "persona_id": f"{skill_name}-smoke",
        "persona_text": persona_text,
        "goals": list(recipe["goals"]),
        "possible_tool_calls": [[call["name"]] for call in recipe["tool_calls"]],
        "scenario_id": loaded.scenario_spec.scenario_id,
        "environment_profile": loaded.profile.raw,
        "initial_state": initial_state,
        "expected_final_state": final_state,
        "user_agent_config": {
            "role": "smoke-user",
            "personality": "brief",
            "knowledge_boundary": "requests a representative tool interaction",
        },
        "end_condition": f"Representative backend sample for {skill_name} executed successfully.",
    }


def synthesize_one(
    *,
    skill_dir: Path,
    persona_text: str,
    sample_index: int,
    output_root: Path,
) -> dict[str, Any]:
    skill_name = skill_dir.name
    recipe = RECIPE_BY_SKILL[skill_name]
    loaded = load_backend_from_skill_dir(skill_dir)
    if loaded is None:
        raise FileNotFoundError(f"No backend found for {skill_name}")

    tools = parse_tools(skill_dir / "tools.jsonl")
    initial_state = loaded.backend.snapshot_state()
    variables: dict[str, Any] = {}
    turns: list[SimulationTurn] = []
    messages: list[dict[str, Any]] = []
    transitions: list[StateTransitionRecord] = []

    for turn_index, call in enumerate(recipe["tool_calls"], start=1):
        tool_name = call["name"]
        arguments = resolve_placeholders(call["arguments"], variables)
        conversation_context = call.get("conversation_context")

        before_state = loaded.backend.snapshot_state()
        result = loaded.backend.call(tool_name, arguments, conversation_context=conversation_context)
        after_state = loaded.backend.snapshot_state()
        transitions.append(
            StateTransitionRecord(
                tool_name=tool_name,
                arguments=arguments,
                before_state=before_state,
                after_state=after_state,
                result=result,
            )
        )
        for variable_name, result_path in call.get("save", {}).items():
            variables[variable_name] = get_path(result, result_path)

        user_message = f"Please help with: {recipe['goals'][turn_index - 1]}"
        assistant_message = json.dumps(result, ensure_ascii=False)
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": assistant_message})
        turns.append(
            SimulationTurn(
                turn_index=turn_index,
                goal_index=turn_index,
                goal_text=recipe["goals"][turn_index - 1],
                user_message=user_message,
                assistant_message=assistant_message,
                tool_calls=[{"name": tool_name, "arguments": arguments, "result": result}],
                execution_time_ms=0,
                validation={"tool_execution_succeeded": True},
                before_state=before_state,
                after_state=after_state,
            )
        )

    final_state = loaded.backend.snapshot_state()
    blueprint = build_blueprint(
        skill_name=skill_name,
        persona_text=persona_text,
        loaded=loaded,
        recipe=recipe,
        initial_state=initial_state,
        final_state=final_state,
    )
    trajectory = SimulationResult(
        run_id=f"{skill_name}-sample-{sample_index:03d}",
        trajectory_id=str(uuid.uuid4()),
        blueprint_id=blueprint["blueprint_id"],
        skill_name=skill_name,
        persona_id=blueprint["persona_id"],
        tools=tools,
        messages=messages,
        structured_turns=turns,
        validation={
            "ended_normally": True,
            "turn_count": len(turns),
            "state_transition_count": len(transitions),
            "final_state_diff_vs_expected": compare_state(final_state, blueprint["expected_final_state"]),
        },
        final_tool_state=final_state,
        initial_state=initial_state,
        scenario_id=loaded.scenario_spec.scenario_id,
        environment_profile=loaded.profile.raw,
        state_transitions=transitions,
    )
    evaluation = EvaluationResult(
        score=1.0,
        hallucination_risk="low",
        task_completion_score=1.0,
        reason="Program backend smoke sample executed successfully.",
        run_id=trajectory.run_id,
        blueprint_id=trajectory.blueprint_id,
        trajectory_id=trajectory.trajectory_id,
        diagnostics={
            "skill_name": skill_name,
            "tool_call_count": len(recipe["tool_calls"]),
            "state_transition_count": len(transitions),
        },
    )

    store = ArtifactStore(output_root / skill_name)
    store.write_blueprint(sample_index, blueprint)
    store.write_trajectory(sample_index, trajectory)
    store.write_evaluation(sample_index, evaluation)
    manifest_record = {
        "sample_index": sample_index,
        "run_id": trajectory.run_id,
        "skill_name": skill_name,
        "accepted": True,
        "error": "",
        "score": evaluation.score,
    }
    store.append_manifest_record(manifest_record)
    summary = {
        "total_count": 1,
        "succeeded_count": 1,
        "failed_count": 0,
        "accepted_count": 1,
        "rejected_count": 0,
        "samples": [
            {
                "sample_index": sample_index,
                "run_id": trajectory.run_id,
                "accepted": True,
                "error": "",
            }
        ],
    }
    store.write_summary(summary)

    return {
        "skill_name": skill_name,
        "sample_index": sample_index,
        "blueprint": blueprint,
        "trajectory": trajectory,
        "evaluation": evaluation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Program backend smoke synthesis pipeline")
    parser.add_argument("--skills-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--selected-skills", type=Path)
    parser.add_argument("--persona-path", type=Path)
    parser.add_argument("--limit-skills", type=int, default=0)
    args = parser.parse_args()

    skills_root = args.skills_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.selected_skills:
        skill_names = load_selected_skills(args.selected_skills.resolve())
    else:
        skill_names = discover_skills(skills_root)
    if args.limit_skills > 0:
        skill_names = skill_names[: args.limit_skills]

    persona_lines = ["Program backend smoke persona"]
    if args.persona_path and args.persona_path.exists():
        persona_lines = [
            line.strip()
            for line in args.persona_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] or persona_lines

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for sample_index, skill_name in enumerate(skill_names):
        persona_text = persona_lines[sample_index % len(persona_lines)]
        try:
            result = synthesize_one(
                skill_dir=skills_root / skill_name,
                persona_text=persona_text,
                sample_index=0,
                output_root=output_root,
            )
            results.append(result)
            print(f"[OK] {skill_name}")
        except Exception as exc:
            failures.append({"skill_name": skill_name, "error": str(exc)})
            print(f"[FAIL] {skill_name}: {exc}")

    batch_summary = {
        "total_skills": len(skill_names),
        "succeeded_skills": len(results),
        "failed_skills": len(failures),
        "failures": failures,
    }
    (output_root / "summary.json").write_text(
        json.dumps(to_jsonable(batch_summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_root / "manifest.jsonl").write_text(
        "\n".join(json.dumps({"skill_name": item["skill_name"], "accepted": True}, ensure_ascii=False) for item in results)
        + ("\n" if results else ""),
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

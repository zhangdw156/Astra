from __future__ import annotations

import json
from pathlib import Path

from astra.agent._planner_agent.agent import PlannerAgent
from astra.agent._planner_agent.config import PlannerAgentConfig


def test_planner_injects_program_fields_before_validation(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md")
    )

    raw_blueprint = {
        "goals": ["Convert centimeters to meters"],
        "possible_tool_calls": [["convert"]],
        "user_agent_config": {
            "role": "analyst",
            "personality": "brief",
            "knowledge_boundary": "does not know tool internals",
        },
        "end_condition": "The conversion is complete.",
    }

    monkeypatch.setattr(agent, "call_model", lambda prompt: json.dumps(raw_blueprint))

    result = agent.generate(
        skill_dir=skill_dir,
        persona_text=persona_text,
    )

    blueprint = result.blueprint
    assert blueprint["scenario_id"] == "default"
    assert blueprint["environment_profile"]["backend_mode"] == "program-direct"
    assert blueprint["environment_profile"]["validation_mode"] == "final_state"
    assert blueprint["initial_state"] == {}


def test_planner_repairs_malformed_blueprint_after_validation_failure(monkeypatch) -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md")
    )

    broken_raw = json.dumps(
        {
            "role": "analyst",
            "personality": "brief",
            "knowledge_boundary": "does not know tool internals",
        }
    )
    repaired_blueprint = {
        "goals": ["Convert centimeters to meters"],
        "possible_tool_calls": [["convert"]],
        "initial_state": {},
        "expected_final_state": {},
        "state_checkpoints": [],
        "user_agent_config": {
            "role": "analyst",
            "personality": "brief",
            "knowledge_boundary": "does not know tool internals",
        },
        "end_condition": "The conversion is complete.",
    }
    repair_calls: list[list[str]] = []

    monkeypatch.setattr(agent, "call_model", lambda prompt: broken_raw)

    def fake_repair_model_output(*, prompt: str, raw_response: str, validation_errors: list[str]) -> str:
        del prompt, raw_response
        repair_calls.append(validation_errors)
        return json.dumps(repaired_blueprint)

    monkeypatch.setattr(agent, "repair_model_output", fake_repair_model_output)

    result = agent.generate(
        skill_dir=skill_dir,
        persona_text=persona_text,
    )

    assert len(repair_calls) == 1
    assert any("缺少必填字段: goals" in item for item in repair_calls[0])
    assert len(result.blueprint["goals"]) >= 2
    assert all(len(group) >= 2 for group in result.blueprint["possible_tool_calls"])
    assert result.blueprint["user_agent_config"]["role"] == "analyst"


def test_normalize_blueprint_moves_stray_user_fields_into_user_agent_config() -> None:
    root = Path(__file__).resolve().parents[1]
    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md")
    )

    normalized = agent.normalize_blueprint(
        {
            "goals": ["a"],
            "possible_tool_calls": [["convert"]],
            "role": "analyst",
            "personality": "brief",
            "knowledge_boundary": "limited",
            "state_checkpoints": None,
        }
    )

    assert normalized["user_agent_config"]["role"] == "analyst"
    assert "role" not in normalized
    assert normalized["state_checkpoints"] == []


def test_normalize_blueprint_expands_multi_tool_goals_when_skill_has_multiple_tools() -> None:
    root = Path(__file__).resolve().parents[1]
    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md")
    )

    normalized = agent.normalize_blueprint(
        {
            "goals": ["Convert centimeters to meters"],
            "possible_tool_calls": [["convert"]],
            "state_checkpoints": [],
        },
        available_tool_names=["convert", "list_units", "categories", "help"],
    )

    assert len(normalized["goals"]) >= 2
    assert len(normalized["goals"]) == len(normalized["possible_tool_calls"])
    assert all(len(group) >= 2 for group in normalized["possible_tool_calls"])
    assert all("convert" in group for group in normalized["possible_tool_calls"])


def test_planner_falls_back_to_deterministic_blueprint_after_repair_failure(
    monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    persona_path = root / "persona" / "persona_5K.jsonl"
    persona_text = persona_path.read_text(encoding="utf-8").splitlines()[0].strip()

    agent = PlannerAgent(
        PlannerAgentConfig(prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md")
    )

    monkeypatch.setattr(
        agent,
        "call_model",
        lambda prompt: json.dumps(
            {
                "role": "analyst",
                "personality": "brief",
                "knowledge_boundary": "limited",
            }
        ),
    )
    monkeypatch.setattr(
        agent,
        "repair_model_output",
        lambda **kwargs: json.dumps(
            {
                "role": "analyst",
                "personality": "brief",
                "knowledge_boundary": "limited",
            }
        ),
    )

    result = agent.generate(skill_dir=skill_dir, persona_text=persona_text)

    assert len(result.blueprint["goals"]) >= 2
    assert len(result.blueprint["goals"]) == len(result.blueprint["possible_tool_calls"])
    assert all(len(group) >= 2 for group in result.blueprint["possible_tool_calls"])
    assert result.blueprint["user_agent_config"]["knowledge_boundary"]

from __future__ import annotations

import json
from pathlib import Path

from astra.agent._planner_agent.prompt_builder import PlannerPromptBuilder
from astra.agent._planner_agent.validator import BlueprintValidator
from astra.agent._tool_agent.config import ToolAgentConfig
from astra.envs.context import load_environment_context
from astra.envs.hybrid import validate_hybrid_result
from astra.envs.loader import load_backend_from_skill_dir
from astra.envs.types import EnvironmentProfile
from astra.envs.validation import compare_state, is_state_match
from astra.simulation import MCPRuntimeConfig, SimulationRunnerConfig
from astra.simulation.mcp_runtime import LocalMCPRuntime
from astra.simulation.runner import SimulationRunner
from astra.simulation.types import SimulationTurn
from astra.agent._user_agent.config import UserAgentConfig


def make_fake_skill_dir(tmp_path: Path) -> Path:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test skill\n", encoding="utf-8")
    (skill_dir / "tools.jsonl").write_text(
        json.dumps(
            {
                "name": "increment",
                "description": "Increment a counter",
                "inputSchema": {
                    "type": "object",
                    "properties": {"amount": {"type": "integer"}},
                    "required": ["amount"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (skill_dir / "environment_profile.json").write_text(
        json.dumps(
            {
                "backend_mode": "program-direct",
                "state_mode": "json",
                "validation_mode": "final_state",
                "scenario_source": "inline",
                "bfcl_analog": "math_api",
                "entry_class": "SkillBackend",
                "tool_names": ["increment"],
                "default_scenario": "default",
                "notes_ref": "notes.md",
                "state_mutation_policy": "programmatic",
                "generated_result_fields": [],
                "generated_text_policy": "none",
            }
        ),
        encoding="utf-8",
    )
    (skill_dir / "backend.py").write_text(
        """
from __future__ import annotations


class SkillBackend:
    def __init__(self, *, skill_dir, profile):
        self.state = {}

    def load_scenario(self, scenario):
        self.state = {"counter": scenario.get("counter", 0)}

    def reset(self):
        self.state = {}

    def call(self, tool_name, arguments, conversation_context=None):
        if tool_name != "increment":
            raise ValueError(tool_name)
        self.state["counter"] += int(arguments["amount"])
        return {"counter": self.state["counter"]}

    def snapshot_state(self):
        return dict(self.state)

    def visible_state(self):
        return dict(self.state)
""".strip()
        + "\n",
        encoding="utf-8",
    )
    scenarios = skill_dir / "scenarios"
    scenarios.mkdir()
    (scenarios / "default.json").write_text(
        json.dumps({"counter": 2}),
        encoding="utf-8",
    )
    return skill_dir


def make_prompt_file(tmp_path: Path) -> Path:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("placeholder {TOOL_NAME}", encoding="utf-8")
    return prompt_path


def test_compare_state_supports_subset_matching() -> None:
    actual = {"a": 1, "b": {"x": 2, "y": 3}, "c": [1, 2, 3]}
    expected = {"b": {"x": 2}, "c": [1, 2]}

    assert is_state_match(actual, expected, subset=True)
    diffs = compare_state(actual, {"b": {"x": 4}}, subset=True)
    assert diffs == [
        {
            "path": "$.b.x",
            "kind": "value_mismatch",
            "expected": 4,
            "actual": 2,
        }
    ]


def test_loader_and_environment_context_read_profile_and_scenario(tmp_path: Path) -> None:
    skill_dir = make_fake_skill_dir(tmp_path)

    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None
    assert loaded.profile.backend_mode == "program-direct"
    assert loaded.scenario_spec.scenario_id == "default"
    assert loaded.scenario == {"counter": 2}

    context = load_environment_context(skill_dir)
    assert context["scenario_id"] == "default"
    assert context["environment_profile"]["backend_mode"] == "program-direct"
    assert context["scenario_summary"]["counter"]["kind"] == "int"


def test_runtime_routes_to_program_executor_and_records_transition(tmp_path: Path) -> None:
    skill_dir = make_fake_skill_dir(tmp_path)
    prompt_path = make_prompt_file(tmp_path)
    runtime = LocalMCPRuntime(
        config=MCPRuntimeConfig(port=18999),
        tool_agent_config=ToolAgentConfig(prompt_path=prompt_path),
        skill_dir=skill_dir,
        tools_path=skill_dir / "tools.jsonl",
        state_key="simulation",
    )

    runtime.reset_state()
    assert runtime.get_state() == {"counter": 2}

    handler = runtime.make_tool_handler(runtime.tools[0])
    result = json.loads(handler(amount=5))
    assert result == {"counter": 7}
    assert runtime.get_state() == {"counter": 7}
    assert len(runtime.state_transitions) == 1
    assert runtime.state_transitions[0].before_state == {"counter": 2}
    assert runtime.state_transitions[0].after_state == {"counter": 7}


def test_runtime_returns_validation_error_for_missing_required_arguments(tmp_path: Path) -> None:
    skill_dir = make_fake_skill_dir(tmp_path)
    prompt_path = make_prompt_file(tmp_path)
    runtime = LocalMCPRuntime(
        config=MCPRuntimeConfig(port=18999),
        tool_agent_config=ToolAgentConfig(prompt_path=prompt_path),
        skill_dir=skill_dir,
        tools_path=skill_dir / "tools.jsonl",
        state_key="simulation",
    )

    runtime.reset_state()
    handler = runtime.make_tool_handler(runtime.tools[0])
    result = json.loads(handler())

    assert result["error"]["type"] == "validation_error"
    assert result["error"]["missing"] == ["amount"]
    assert runtime.get_state() == {"counter": 2}
    assert runtime.state_transitions == []


def test_runtime_returns_validation_error_for_none_required_argument(tmp_path: Path) -> None:
    skill_dir = make_fake_skill_dir(tmp_path)
    prompt_path = make_prompt_file(tmp_path)
    runtime = LocalMCPRuntime(
        config=MCPRuntimeConfig(port=18999),
        tool_agent_config=ToolAgentConfig(prompt_path=prompt_path),
        skill_dir=skill_dir,
        tools_path=skill_dir / "tools.jsonl",
        state_key="simulation",
    )

    runtime.reset_state()
    handler = runtime.make_tool_handler(runtime.tools[0])
    result = json.loads(handler(amount=None))

    assert result["error"]["type"] == "validation_error"
    assert result["error"]["missing"] == ["amount"]
    assert runtime.get_state() == {"counter": 2}
    assert runtime.state_transitions == []


def test_blueprint_validator_accepts_v2_fields() -> None:
    data = {
        "goals": ["increment counter"],
        "possible_tool_calls": [["increment"]],
        "scenario_id": "default",
        "environment_profile": {
            "backend_mode": "program-direct",
            "validation_mode": "final_state",
            "state_mutation_policy": "programmatic",
            "generated_result_fields": [],
            "generated_text_policy": "none",
        },
        "initial_state": {"counter": 2},
        "expected_final_state": {"counter": 7},
        "state_checkpoints": [{"turn_index": 1, "expected_state": {"counter": 7}}],
        "user_agent_config": {
            "role": "tester",
            "personality": "brief",
            "knowledge_boundary": "does not know tool internals",
        },
        "end_condition": "counter updated",
    }

    assert BlueprintValidator.validate(data, allowed_tool_names={"increment"}) == []


def test_validate_hybrid_result_requires_declared_generated_fields_to_be_text() -> None:
    skill_dir = Path("/tmp/fake")
    profile = EnvironmentProfile(
        skill_dir=skill_dir,
        backend_mode="hybrid",
        validation_mode="turn_state",
        state_mutation_policy="programmatic",
        generated_result_fields=("summary",),
        generated_text_policy="templated-summary",
        raw={},
    )

    validate_hybrid_result(profile=profile, result={"summary": "ok", "memory": {"id": "m1"}})

    try:
        validate_hybrid_result(profile=profile, result={"summary": {"bad": True}})
    except ValueError as exc:
        assert "generated field" in str(exc)
    else:
        raise AssertionError("Expected hybrid result validation failure")


def test_planner_prompt_builder_renders_environment_placeholders(tmp_path: Path) -> None:
    prompt_path = tmp_path / "planner_prompt.md"
    prompt_path.write_text(
        "SKILL={SKILL_MD_CONTENT}\nTOOLS={TOOLS_JSONL_CONTENT}\nPERSONA={PERSONA_CONTENT}\nENV={ENVIRONMENT_PROFILE}\nSCENARIO={SCENARIO_SUMMARY}",
        encoding="utf-8",
    )
    builder = PlannerPromptBuilder(prompt_path)
    prompt = builder.build(
        skill_md_content="skill",
        tools_jsonl_content="tools",
        persona_content="persona",
        environment_profile='{"backend_mode":"program-direct"}',
        scenario_summary='{"counter":{"kind":"int"}}',
    )
    assert 'ENV={"backend_mode":"program-direct"}' in prompt
    assert 'SCENARIO={"counter":{"kind":"int"}}' in prompt


def test_runner_final_validation_uses_state_diff_and_checkpoints(tmp_path: Path) -> None:
    prompt_path = tmp_path / "user_prompt.md"
    prompt_path.write_text("user prompt", encoding="utf-8")
    runner = SimulationRunner(
        config=SimulationRunnerConfig(),
        user_agent_config=UserAgentConfig(prompt_path=prompt_path),
        tool_agent_config=ToolAgentConfig(prompt_path=prompt_path),
    )

    turns = [
        SimulationTurn(
            turn_index=1,
            goal_index=1,
            goal_text="increment",
            user_message="do it",
            assistant_message="done",
            tool_calls=[],
            execution_time_ms=1,
            validation={},
            before_state={"counter": 2},
            after_state={"counter": 7},
        )
    ]
    validation = runner.build_final_validation(
        blueprint={
            "goals": ["increment"],
            "expected_final_state": {"counter": 7},
            "state_checkpoints": [{"turn_index": 1, "expected_state": {"counter": 7}}],
        },
        turns=turns,
        final_tool_state={"counter": 7},
        ended_normally=True,
        hit_max_turns=False,
    )

    assert validation["final_state_match"] is True
    assert validation["state_checkpoints"] == [{"turn_index": 1, "diffs": []}]

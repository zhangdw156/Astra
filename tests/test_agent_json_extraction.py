from __future__ import annotations

from astra.agent._eval_agent.validator import EvalAgentValidator
from astra.agent._planner_agent.validator import BlueprintValidator


def test_eval_validator_accepts_trailing_text_after_json() -> None:
    parsed = EvalAgentValidator.extract_json_from_response(
        '{"score": 4.5, "hallucination_risk": "low", "task_completion_score": 0.9, "reason": "Sentence one. Sentence two."}\nExtra explanation'
    )

    assert parsed["score"] == 4.5
    assert parsed["hallucination_risk"] == "low"


def test_planner_validator_accepts_trailing_text_after_json() -> None:
    parsed = BlueprintValidator.extract_json_from_response(
        '{"goals":["a"],"possible_tool_calls":[["tree"]],"user_agent_config":{"role":"r","personality":"p","knowledge_boundary":"k"},"end_condition":"done"}\nMore notes'
    )

    assert parsed["goals"] == ["a"]
    assert parsed["possible_tool_calls"] == [["tree"]]


def test_eval_validator_accepts_fenced_json_with_suffix() -> None:
    parsed = EvalAgentValidator.extract_json_from_response(
        '```json\n{"score": 3.0, "hallucination_risk": "none", "task_completion_score": 1.0, "reason": "Sentence one. Sentence two."}\n```\nTrailing text'
    )

    assert parsed["task_completion_score"] == 1.0


def test_planner_validator_prefers_full_blueprint_over_leading_object() -> None:
    parsed = BlueprintValidator.extract_json_from_response(
        '\n'.join(
            [
                '分析过程里的小对象: {"scenario_id":"default","initial_state":{},"state_checkpoints":[]}',
                '{"goals":["find helper"],"possible_tool_calls":[["grep","read"]],"user_agent_config":{"role":"engineer","personality":"careful","knowledge_boundary":"repo only"},"end_condition":"found helper","scenario_id":"default","environment_profile":{"backend_mode":"program-fixture","validation_mode":"turn_state"},"initial_state":{},"state_checkpoints":[]}',
            ]
        )
    )

    assert parsed["goals"] == ["find helper"]
    assert parsed["possible_tool_calls"] == [["grep", "read"]]


def test_eval_validator_prefers_full_result_over_leading_object() -> None:
    parsed = EvalAgentValidator.extract_json_from_response(
        '\n'.join(
            [
                '中间统计: {"score": 4.0}',
                '{"score": 4.0, "hallucination_risk": "none", "task_completion_score": 1.0, "reason": "Sentence one. Sentence two."}',
            ]
        )
    )

    assert parsed["hallucination_risk"] == "none"
    assert parsed["task_completion_score"] == 1.0

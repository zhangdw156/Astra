from __future__ import annotations

import json
from pathlib import Path

from astra.agent._eval_agent.types import EvaluationBundle, EvaluationResult
from astra.agent._eval_agent_v2 import EvalAgentV2, EvalAgentV2Config


class _FakeExecutor:
    def __init__(self, handler):
        self.handler = handler
        self.calls: list[str] = []

    def run(self, task_text: str, cwd: Path, verbose: bool = False) -> int:
        del cwd, verbose
        self.calls.append(task_text)
        return self.handler(task_text, len(self.calls))


def _extract_path(task_text: str, marker: str) -> Path:
    for line in task_text.splitlines():
        line = line.strip()
        if line.startswith(marker):
            return Path(line[len(marker) :].strip().strip("`"))
    raise AssertionError(f"marker not found: {marker}")


def test_eval_agent_v2_reads_output_and_returns_artifacts(tmp_path: Path) -> None:
    prompt_path = tmp_path / "eval_agent_v2.md"
    prompt_path.write_text(
        "Skill: {SKILL_DIR}\nBlueprint: {BLUEPRINT_PATH}\nTrajectory: {TRAJECTORY_PATH}\n"
        "Eval: {EVALUATION_OUTPUT_PATH}\nReview: {REVIEW_OUTPUT_PATH}\n"
        "{EVALUATION_SCHEMA}\n{REVIEW_SCHEMA}\n{AVAILABLE_CAPABILITIES}\n"
        "{EVALUATION_WORKFLOW}\n{EVALUATION_RULES}\n{REPAIR_POLICY}\n",
        encoding="utf-8",
    )

    def handler(task_text: str, call_count: int) -> int:
        del call_count
        evaluation_path = _extract_path(task_text, "Eval:")
        review_path = _extract_path(task_text, "Review:")
        evaluation_path.write_text(
            json.dumps(
                {
                    "score": 4.2,
                    "hallucination_risk": "none",
                    "task_completion_score": 1.0,
                    "reason": "The assistant stays grounded and completes the task. The blueprint still has a minor formatting defect.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        review_path.write_text(
            json.dumps(
                {
                    "summary": "The sample is strong but a minor trajectory normalization would help.",
                    "strongest_positive": "The task is completed with grounded tool use.",
                    "strongest_negative": "A formatting issue still makes the artifact awkward.",
                    "root_causes": ["formatting", "blueprint schema mismatch"],
                    "should_repair": True,
                    "repair_target": "trajectory",
                    "repair_strategy": "Normalize the trajectory into a cleaner tool-calling SFT export.",
                    "export_training_artifact": True,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0

    agent = EvalAgentV2(
        EvalAgentV2Config(prompt_path=prompt_path, project_root=tmp_path),
        executor=_FakeExecutor(handler),
    )
    bundle = agent.evaluate(
        blueprint={
            "blueprint_id": "bp1",
            "goals": ["send a message"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        trajectory={
            "run_id": "run1",
            "trajectory_id": "tr1",
            "skill_name": "1534_voipms-sms",
            "tools": [
                {
                    "name": "skill-tools-send_sms",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ],
            "messages": [
                {"role": "user", "content": "Please text Chris."},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "skill-tools-send_sms",
                                "arguments": "{\"dst\":\"+15551234567\"}",
                            }
                        }
                    ],
                },
                {"role": "tool", "content": "{\"ok\": true}"},
            ],
            "validation": {"final_state_match": True, "state_checkpoints": []},
        },
        skill_dir=tmp_path,
    )

    assert bundle.result.score == 4.2
    assert bundle.artifacts is not None
    assert bundle.artifacts["review"]["repair_target"] == "trajectory"
    assert (
        bundle.artifacts["training_export"]["format"]
        == "qwen3_tool_calling_sft_repair_candidate"
    )
    assert (
        bundle.artifacts["training_export"]["trajectory_qwen3_sft"]["messages"][0]["role"]
        == "system"
    )


def test_eval_agent_v2_accepts_free_form_review_root_causes(tmp_path: Path) -> None:
    prompt_path = tmp_path / "eval_agent_v2.md"
    prompt_path.write_text(
        "Eval: {EVALUATION_OUTPUT_PATH}\nReview: {REVIEW_OUTPUT_PATH}\n"
        "{EVALUATION_SCHEMA}\n{REVIEW_SCHEMA}\n{AVAILABLE_CAPABILITIES}\n"
        "{EVALUATION_WORKFLOW}\n{EVALUATION_RULES}\n{REPAIR_POLICY}\n"
        "Skill: {SKILL_DIR}\nBlueprint: {BLUEPRINT_PATH}\nTrajectory: {TRAJECTORY_PATH}\n",
        encoding="utf-8",
    )

    def handler(task_text: str, call_count: int) -> int:
        del call_count
        evaluation_path = _extract_path(task_text, "Eval:")
        review_path = _extract_path(task_text, "Review:")
        evaluation_path.write_text(
            json.dumps(
                {
                    "score": 4.1,
                    "hallucination_risk": "none",
                    "task_completion_score": 1.0,
                    "reason": "Sentence one. Sentence two.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        review_path.write_text(
            json.dumps(
                {
                    "summary": "Minor mismatch remains.",
                    "strongest_positive": "The task is completed.",
                    "strongest_negative": "The blueprint shape is slightly awkward.",
                    "root_causes": ["schema mismatch", "environment summary drift"],
                    "should_repair": False,
                    "repair_target": "none",
                    "repair_strategy": "",
                    "export_training_artifact": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0

    agent = EvalAgentV2(
        EvalAgentV2Config(prompt_path=prompt_path, project_root=tmp_path),
        executor=_FakeExecutor(handler),
    )
    bundle = agent.evaluate(
        blueprint={
            "blueprint_id": "bp1",
            "goals": ["send a message"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        trajectory={
            "run_id": "run1",
            "trajectory_id": "tr1",
            "messages": [],
            "validation": {"final_state_match": False, "state_checkpoints": []},
        },
        skill_dir=tmp_path,
    )
    assert bundle.artifacts is not None
    assert bundle.artifacts["review"]["root_causes"] == [
        "schema mismatch",
        "environment summary drift",
    ]


def test_eval_agent_v2_repairs_invalid_output_once(tmp_path: Path) -> None:
    prompt_path = tmp_path / "eval_agent_v2.md"
    prompt_path.write_text(
        "Eval: {EVALUATION_OUTPUT_PATH}\nReview: {REVIEW_OUTPUT_PATH}\n"
        "{EVALUATION_SCHEMA}\n{REVIEW_SCHEMA}\n{AVAILABLE_CAPABILITIES}\n"
        "{EVALUATION_WORKFLOW}\n{EVALUATION_RULES}\n{REPAIR_POLICY}\n"
        "Skill: {SKILL_DIR}\nBlueprint: {BLUEPRINT_PATH}\nTrajectory: {TRAJECTORY_PATH}\n",
        encoding="utf-8",
    )

    def handler(task_text: str, call_count: int) -> int:
        evaluation_path = _extract_path(task_text, "Eval:")
        if call_count == 1:
            evaluation_path.write_text(
                json.dumps(
                    {
                        "score": 10.0,
                        "hallucination_risk": "none",
                        "task_completion_score": 1.0,
                        "reason": "Sentence one. Sentence two.",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        else:
            evaluation_path.write_text(
                json.dumps(
                    {
                        "score": 4.0,
                        "hallucination_risk": "low",
                        "task_completion_score": 0.9,
                        "reason": "Sentence one. Sentence two.",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        return 0

    executor = _FakeExecutor(handler)
    agent = EvalAgentV2(
        EvalAgentV2Config(prompt_path=prompt_path, project_root=tmp_path, repair_attempts=1),
        executor=executor,
    )
    bundle = agent.evaluate(
        blueprint={
            "blueprint_id": "bp1",
            "goals": ["goal"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        trajectory={"run_id": "run1", "trajectory_id": "tr1", "messages": [], "validation": {}},
        skill_dir=tmp_path,
    )
    assert bundle.result.score == 4.0
    assert len(executor.calls) == 2


def test_eval_agent_v2_falls_back_to_legacy_eval(tmp_path: Path, monkeypatch) -> None:
    prompt_path = tmp_path / "eval_agent_v2.md"
    prompt_path.write_text(
        "{SKILL_DIR}{BLUEPRINT_PATH}{TRAJECTORY_PATH}{EVALUATION_OUTPUT_PATH}{REVIEW_OUTPUT_PATH}"
        "{EVALUATION_SCHEMA}{REVIEW_SCHEMA}{AVAILABLE_CAPABILITIES}{EVALUATION_WORKFLOW}"
        "{EVALUATION_RULES}{REPAIR_POLICY}",
        encoding="utf-8",
    )

    agent = EvalAgentV2(
        EvalAgentV2Config(prompt_path=prompt_path, project_root=tmp_path),
        executor=_FakeExecutor(lambda task_text, call_count: 1),
    )
    monkeypatch.setattr(
        agent.legacy,
        "evaluate",
        lambda **kwargs: EvaluationBundle(
            result=EvaluationResult(
                score=3.5,
                hallucination_risk="low",
                task_completion_score=0.7,
                reason="Sentence one. Sentence two.",
            ),
            prompt="legacy",
            raw_response="{}",
        ),
    )
    bundle = agent.evaluate(
        blueprint={
            "blueprint_id": "bp1",
            "goals": ["goal"],
            "user_agent_config": {},
            "end_condition": "done",
        },
        trajectory={"run_id": "run1", "trajectory_id": "tr1", "messages": [], "validation": {}},
        skill_dir=tmp_path,
    )
    assert bundle.prompt == "legacy"
    assert bundle.result.score == 3.5

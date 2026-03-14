from __future__ import annotations

from pathlib import Path

from astra.agent._eval_agent.types import EvaluationBundle, EvaluationResult
from astra.agent._planner_agent.types import BlueprintResult
from astra.simulation.config import SynthesisPipelineConfig
from astra.simulation.pipeline import SynthesisPipeline
from astra.simulation.types import SimulationResult


def _make_blueprint(*, skill_name: str) -> dict:
    return {
        "blueprint_id": "bp-1",
        "skill_name": skill_name,
        "persona_id": "persona-1",
        "created_at": "2026-03-14T00:00:00+00:00",
        "goals": ["Convert a measurement"],
        "possible_tool_calls": [["convert"]],
        "scenario_id": "default",
        "environment_profile": {
            "backend_mode": "program-direct",
            "validation_mode": "final_state",
        },
        "initial_state": {},
        "expected_final_state": {},
        "state_checkpoints": [],
        "user_agent_config": {
            "role": "tester",
            "personality": "brief and direct",
            "knowledge_boundary": "does not know internal implementation details",
        },
        "end_condition": "The conversion is complete.",
    }


def _make_trajectory(*, skill_name: str) -> SimulationResult:
    return SimulationResult(
        run_id="sample_000000",
        trajectory_id="traj-1",
        blueprint_id="bp-1",
        skill_name=skill_name,
        persona_id="persona-1",
        tools=[],
        messages=[],
        structured_turns=[],
        validation={},
        final_tool_state={},
        initial_state={},
        scenario_id="default",
        environment_profile={"backend_mode": "program-direct"},
        state_transitions=[],
    )


class _FakePlanner:
    def generate(self, *, skill_dir: Path, persona_text: str) -> BlueprintResult:
        return BlueprintResult(
            blueprint=_make_blueprint(skill_name=skill_dir.name),
            raw_response="{}",
            prompt="prompt",
            skill_dir=skill_dir,
            persona_text=persona_text,
        )


class _FakeRunner:
    def __init__(self, *, result: SimulationResult | None = None, exc: Exception | None = None):
        self._result = result
        self._exc = exc

    def build_runtime(self, *, skill_dir: Path, tools_path: Path):
        raise AssertionError("build_runtime should not be called when reuse_runtime=False")

    def run(self, **_: object) -> SimulationResult:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


class _FakeEval:
    def __init__(self, *, result: EvaluationResult | None = None, exc: Exception | None = None):
        self._result = result
        self._exc = exc

    def evaluate(self, **_: object) -> EvaluationBundle:
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return EvaluationBundle(result=self._result, prompt="prompt", raw_response="{}")


def test_run_batch_persists_blueprint_before_runner_failure(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    pipeline = SynthesisPipeline(
        config=SynthesisPipelineConfig(
            output_root=tmp_path,
            evaluate_after_run=True,
            reuse_runtime=False,
            save_blueprint=True,
            save_trajectory=True,
            save_evaluation=True,
            save_manifest=True,
        ),
        planner_agent=_FakePlanner(),
        simulation_runner=_FakeRunner(exc=RuntimeError("runner boom")),
        eval_agent=_FakeEval(
            result=EvaluationResult(
                score=5.0,
                hallucination_risk="none",
                task_completion_score=1.0,
                reason="Sentence one. Sentence two.",
            )
        ),
    )

    batch = pipeline.run_batch(
        skill_dir=skill_dir,
        persona_texts=['{"persona":"demo","id":"persona-1"}'],
    )

    assert batch.failed_count == 1
    assert (tmp_path / "0" / "blueprint.json").exists()
    assert not (tmp_path / "0" / "trajectory.json").exists()
    assert not (tmp_path / "0" / "evaluation.json").exists()
    manifest = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8")
    assert "runner boom" in manifest


def test_run_batch_persists_trajectory_before_eval_failure(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    pipeline = SynthesisPipeline(
        config=SynthesisPipelineConfig(
            output_root=tmp_path,
            evaluate_after_run=True,
            reuse_runtime=False,
            save_blueprint=True,
            save_trajectory=True,
            save_evaluation=True,
            save_manifest=True,
        ),
        planner_agent=_FakePlanner(),
        simulation_runner=_FakeRunner(result=_make_trajectory(skill_name=skill_dir.name)),
        eval_agent=_FakeEval(exc=RuntimeError("eval boom")),
    )

    batch = pipeline.run_batch(
        skill_dir=skill_dir,
        persona_texts=['{"persona":"demo","id":"persona-1"}'],
    )

    assert batch.failed_count == 1
    assert (tmp_path / "0" / "blueprint.json").exists()
    assert (tmp_path / "0" / "trajectory.json").exists()
    assert not (tmp_path / "0" / "evaluation.json").exists()
    manifest = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8")
    assert "eval boom" in manifest

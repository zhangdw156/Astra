from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "exps"
        / "data_synthesis_workflow"
        / "pipeline4_selected_skills_agentic.py"
    )
    spec = importlib.util.spec_from_file_location(
        "pipeline4_selected_skills_agentic", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_discover_program_skills_finds_migrated_skill_dirs() -> None:
    module = load_module()
    skills_root = Path(__file__).resolve().parents[1] / "artifacts" / "env_top30_skills"
    discovered = module.discover_program_skills(skills_root)
    discovered_names = {record["dir_name"] for record in discovered}

    assert "3429_unit-convert" in discovered_names
    assert "1822_code-search" in discovered_names
    assert "6287_math-solver" in discovered_names


def test_validate_program_skill_dir_rejects_incomplete_skill(tmp_path: Path) -> None:
    module = load_module()
    skill_dir = tmp_path / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("demo", encoding="utf-8")

    try:
        module.validate_program_skill_dir(skill_dir)
    except FileNotFoundError as exc:
        assert "tools.jsonl" in str(exc)
        assert "environment_profile.json" in str(exc)
        assert "backend.py" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_build_agents_and_pipeline_uses_shorter_max_turn_budget(tmp_path: Path) -> None:
    module = load_module()
    root = Path(__file__).resolve().parents[1]
    pipeline = module.build_agents_and_pipeline(
        output_root=tmp_path,
        planner_prompt_path=root / "src" / "astra" / "prompts" / "planner_agent.md",
        user_prompt_path=root / "src" / "astra" / "prompts" / "user_agent.md",
        tool_prompt_path=root / "src" / "astra" / "prompts" / "tool_agent.md",
        eval_prompt_path=root / "src" / "astra" / "prompts" / "eval_agent.md",
        port=18000,
    )

    assert pipeline.simulation_runner.config.max_turns == 12


class _FakeRuntime:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


class _FakeRunner:
    def __init__(self) -> None:
        self.runtime = _FakeRuntime()

    def build_runtime(self, *, skill_dir: Path, tools_path: Path) -> _FakeRuntime:
        return self.runtime


class _FakePipeline:
    def __init__(self, output_root: Path) -> None:
        self.config = type(
            "Config",
            (),
            {
                "output_root": output_root,
                "reuse_runtime": True,
            },
        )()
        self.simulation_runner = _FakeRunner()
        self.run_calls: list[int] = []
        self.persisted: list[int] = []

    def run_sample(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
        sample_index: int,
        tools_path: Path | None = None,
        run_id: str | None = None,
        runtime=None,
    ):
        self.run_calls.append(sample_index)
        return type(
            "Result",
            (),
            {
                "sample_index": sample_index,
                "run_id": run_id or f"sample_{sample_index:06d}",
                "blueprint": {"blueprint_id": f"bp-{sample_index}"},
                "trajectory": type("Traj", (), {"trajectory_id": f"traj-{sample_index}"})(),
                "evaluation": type(
                    "Eval",
                    (),
                    {
                        "score": 4.2,
                        "hallucination_risk": "none",
                        "task_completion_score": 1.0,
                    },
                )(),
                "accepted": True,
                "error": "",
            },
        )()

    def persist_sample(self, *, store, result) -> None:
        self.persisted.append(result.sample_index)
        sample_dir = store.sample_dir(result.sample_index)
        (sample_dir / "blueprint.json").write_text(
            json.dumps(result.blueprint),
            encoding="utf-8",
        )
        (sample_dir / "trajectory.json").write_text(
            json.dumps({"trajectory_id": result.trajectory.trajectory_id}),
            encoding="utf-8",
        )
        (sample_dir / "evaluation.json").write_text(
            json.dumps(
                {
                    "score": result.evaluation.score,
                    "hallucination_risk": result.evaluation.hallucination_risk,
                    "task_completion_score": result.evaluation.task_completion_score,
                }
            ),
            encoding="utf-8",
        )

    def build_manifest_record(self, *, result) -> dict:
        return {
            "sample_index": result.sample_index,
            "run_id": result.run_id,
            "accepted": result.accepted,
            "error": result.error,
            "blueprint_id": result.blueprint["blueprint_id"],
            "trajectory_id": result.trajectory.trajectory_id,
            "score": result.evaluation.score,
            "hallucination_risk": result.evaluation.hallucination_risk,
            "task_completion_score": result.evaluation.task_completion_score,
        }

    def decide_acceptance(self, evaluation) -> bool:
        return evaluation.score >= 4.0 and evaluation.hallucination_risk == "none"


def _write_completed_sample(root: Path, sample_index: int) -> None:
    sample_dir = root / str(sample_index)
    sample_dir.mkdir(parents=True)
    (sample_dir / "blueprint.json").write_text(
        json.dumps({"blueprint_id": f"bp-{sample_index}"}),
        encoding="utf-8",
    )
    (sample_dir / "trajectory.json").write_text(
        json.dumps({"trajectory_id": f"traj-{sample_index}"}),
        encoding="utf-8",
    )
    (sample_dir / "evaluation.json").write_text(
        json.dumps(
            {
                "score": 4.5,
                "hallucination_risk": "none",
                "task_completion_score": 1.0,
            }
        ),
        encoding="utf-8",
    )


def test_run_batch_with_resume_skips_completed_samples(tmp_path: Path) -> None:
    module = load_module()
    _write_completed_sample(tmp_path, 0)
    (tmp_path / "manifest.jsonl").write_text(
        json.dumps(
            {
                "sample_index": 0,
                "run_id": "sample_000000",
                "accepted": True,
                "error": "",
                "blueprint_id": "bp-0",
                "trajectory_id": "traj-0",
                "score": 4.5,
                "hallucination_risk": "none",
                "task_completion_score": 1.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    pipeline = _FakePipeline(tmp_path)
    batch = module.run_batch_with_resume(
        pipeline=pipeline,
        skill_dir=tmp_path,
        tools_path=tmp_path / "tools.jsonl",
        persona_texts=["p0", "p1", "p2"],
    )

    assert pipeline.run_calls == [1, 2]
    assert pipeline.persisted == [1, 2]
    assert batch.succeeded_count == 3
    assert batch.failed_count == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["completed_count"] == 3
    assert summary["remaining_count"] == 0


def test_run_batch_with_resume_reruns_incomplete_samples(tmp_path: Path) -> None:
    module = load_module()
    sample_dir = tmp_path / "0"
    sample_dir.mkdir(parents=True)
    (sample_dir / "blueprint.json").write_text(
        json.dumps({"blueprint_id": "bp-0"}),
        encoding="utf-8",
    )
    (sample_dir / "trajectory.json").write_text(
        json.dumps({"trajectory_id": "traj-0"}),
        encoding="utf-8",
    )

    pipeline = _FakePipeline(tmp_path)
    batch = module.run_batch_with_resume(
        pipeline=pipeline,
        skill_dir=tmp_path,
        tools_path=tmp_path / "tools.jsonl",
        persona_texts=["p0"],
    )

    assert pipeline.run_calls == [0]
    assert batch.succeeded_count == 1
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(manifest_lines) == 1
    record = json.loads(manifest_lines[0])
    assert record["sample_index"] == 0
    assert record["accepted"] is True

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "exps" / "data_synthesis_workflow" / "pipeline3_program_backend_batch.py"
    spec = importlib.util.spec_from_file_location("pipeline3_program_backend_batch", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_pipeline_runs_multiple_samples_and_aggregates_summary(tmp_path: Path) -> None:
    module = load_module()
    pipeline2 = module.load_pipeline2_module()
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"

    skill_name, succeeded, failed = module.run_one_skill(
        pipeline2=pipeline2,
        skill_dir=skill_dir,
        output_root=tmp_path,
        persona_lines=["persona one", "persona two"],
        count_per_skill=2,
        shuffle_personas=False,
        seed=42,
    )

    assert skill_name == "3429_unit-convert"
    assert succeeded == 2
    assert failed == 0
    assert (tmp_path / "3429_unit-convert" / "0" / "blueprint.json").exists()
    assert (tmp_path / "3429_unit-convert" / "1" / "trajectory.json").exists()

    summary = json.loads((tmp_path / "3429_unit-convert" / "summary.json").read_text(encoding="utf-8"))
    assert summary["total_count"] == 2
    assert summary["succeeded_count"] == 2
    assert summary["failed_count"] == 0


def test_batch_pipeline_selects_requested_persona_count() -> None:
    module = load_module()
    personas = module.select_personas_for_skill(
        persona_lines=["a", "b"],
        count_per_skill=5,
        shuffle_personas=True,
        seed=42,
        skill_name="3429_unit-convert",
    )
    assert len(personas) == 5

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "exps" / "data_synthesis_workflow" / "pipeline2_program_backend_smoke.py"
    spec = importlib.util.spec_from_file_location("pipeline2_program_backend_smoke", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_pipeline_has_recipe_for_every_migrated_skill() -> None:
    module = load_module()
    skills_root = Path(__file__).resolve().parents[1] / "artifacts" / "env_top30_skills"
    discovered = set(module.discover_skills(skills_root))
    assert discovered == set(module.RECIPE_BY_SKILL)


def test_smoke_pipeline_synthesizes_sample_and_writes_artifacts(tmp_path: Path) -> None:
    module = load_module()
    root = Path(__file__).resolve().parents[1]
    skill_dir = root / "artifacts" / "env_top30_skills" / "3429_unit-convert"
    result = module.synthesize_one(
        skill_dir=skill_dir,
        persona_text="smoke persona",
        sample_index=0,
        output_root=tmp_path,
    )
    assert result["evaluation"].score == 1.0
    assert (tmp_path / "3429_unit-convert" / "0" / "blueprint.json").exists()
    assert (tmp_path / "3429_unit-convert" / "0" / "trajectory.json").exists()
    assert (tmp_path / "3429_unit-convert" / "0" / "evaluation.json").exists()

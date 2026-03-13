from __future__ import annotations

import importlib.util
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

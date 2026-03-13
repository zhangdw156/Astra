from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .base import SkillBackendProtocol
from .types import EnvironmentProfile, ScenarioSpec


@dataclass(slots=True)
class LoadedBackend:
    profile: EnvironmentProfile
    backend: SkillBackendProtocol
    scenario_spec: ScenarioSpec
    scenario: dict[str, Any]


def load_backend_from_skill_dir(
    skill_dir: Path,
    *,
    scenario_id: str | None = None,
) -> LoadedBackend | None:
    skill_dir = skill_dir.resolve()
    profile_path = skill_dir / "environment_profile.json"
    backend_path = skill_dir / "backend.py"

    if not profile_path.exists() or not backend_path.exists():
        return None

    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = EnvironmentProfile(
        skill_dir=skill_dir,
        backend_mode=str(profile_data.get("backend_mode", "llm-fallback")),
        state_mode=str(profile_data.get("state_mode", "json")),
        validation_mode=str(profile_data.get("validation_mode", "none")),
        scenario_source=str(profile_data.get("scenario_source", "inline")),
        bfcl_analog=str(profile_data.get("bfcl_analog", "")),
        entry_class=str(profile_data.get("entry_class", "SkillBackend")),
        tool_names=tuple(
            name for name in profile_data.get("tool_names", []) if isinstance(name, str)
        ),
        default_scenario=str(profile_data.get("default_scenario", "default")),
        notes_ref=str(profile_data.get("notes_ref", "")),
        state_mutation_policy=str(
            profile_data.get("state_mutation_policy", "programmatic")
        ),
        generated_result_fields=tuple(
            item
            for item in profile_data.get("generated_result_fields", [])
            if isinstance(item, str)
        ),
        generated_text_policy=str(profile_data.get("generated_text_policy", "none")),
        raw=profile_data,
    )

    scenario_spec = resolve_scenario_spec(
        skill_dir=skill_dir,
        profile=profile,
        scenario_id=scenario_id,
    )
    scenario = {}
    if scenario_spec.path.exists():
        scenario = json.loads(scenario_spec.path.read_text(encoding="utf-8"))

    module = _load_module_from_path(
        module_name=f"astra_skill_backend_{skill_dir.name}",
        file_path=backend_path,
    )
    backend_cls = getattr(module, profile.entry_class)
    backend = backend_cls(skill_dir=skill_dir, profile=profile_data)
    backend.load_scenario(scenario)

    return LoadedBackend(
        profile=profile,
        backend=backend,
        scenario_spec=scenario_spec,
        scenario=scenario,
    )


def resolve_scenario_spec(
    *,
    skill_dir: Path,
    profile: EnvironmentProfile,
    scenario_id: str | None = None,
) -> ScenarioSpec:
    active_scenario_id = scenario_id or profile.default_scenario
    scenarios_dir = skill_dir / "scenarios"
    scenario_path = scenarios_dir / f"{active_scenario_id}.json"
    summary: dict[str, Any] = {}
    if scenario_path.exists():
        try:
            summary = json.loads(scenario_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary = {}

    return ScenarioSpec(
        scenario_id=active_scenario_id,
        path=scenario_path,
        source=profile.scenario_source,
        summary=build_scenario_summary(summary),
    )


def build_scenario_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        return {}

    summary: dict[str, Any] = {}
    for key, value in scenario.items():
        if isinstance(value, list):
            summary[key] = {"kind": "list", "size": len(value)}
        elif isinstance(value, dict):
            summary[key] = {"kind": "dict", "keys": sorted(value.keys())[:10]}
        else:
            summary[key] = {"kind": type(value).__name__}
    return summary


def _load_module_from_path(*, module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from path: {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

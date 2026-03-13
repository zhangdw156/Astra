from __future__ import annotations

import json
from pathlib import Path

from .loader import resolve_scenario_spec
from .types import EnvironmentProfile


def load_environment_context(skill_dir: Path) -> dict:
    profile_path = skill_dir / "environment_profile.json"
    if not profile_path.exists():
        return {}

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
    scenario_spec = resolve_scenario_spec(skill_dir=skill_dir, profile=profile)
    return {
        "environment_profile": profile.raw,
        "scenario_id": scenario_spec.scenario_id,
        "scenario_summary": scenario_spec.summary,
    }


def render_environment_summary(context: dict) -> str:
    if not context:
        return "(no environment profile)"
    return json.dumps(context.get("environment_profile", {}), ensure_ascii=False, indent=2)


def render_scenario_summary(context: dict) -> str:
    if not context:
        return "(no scenario summary)"
    return json.dumps(context.get("scenario_summary", {}), ensure_ascii=False, indent=2)

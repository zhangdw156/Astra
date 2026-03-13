from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class EnvironmentProfile:
    skill_dir: Path
    backend_mode: str
    state_mode: str = "json"
    validation_mode: str = "none"
    scenario_source: str = "inline"
    bfcl_analog: str = ""
    entry_class: str = "SkillBackend"
    tool_names: tuple[str, ...] = ()
    default_scenario: str = "default"
    notes_ref: str = ""
    state_mutation_policy: str = "programmatic"
    generated_result_fields: tuple[str, ...] = ()
    generated_text_policy: str = "none"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    path: Path
    source: str = "inline"
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StateTransitionRecord:
    tool_name: str
    arguments: dict[str, Any]
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    result: dict[str, Any]

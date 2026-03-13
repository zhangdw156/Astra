from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PlannerRunContext:
    """
    PlannerAgent 单次运行的上下文。
    """

    skill_dir: Path
    skill_md_path: Path
    tools_jsonl_path: Path
    environment_profile_path: Path | None = None
    scenario_dir: Path | None = None
    environment_profile_summary: dict[str, Any] | None = None
    scenario_summary: dict[str, Any] | None = None


@dataclass(slots=True)
class BlueprintResult:
    """
    一次 blueprint 生成的结果。
    """

    blueprint: dict
    raw_response: str
    prompt: str
    skill_dir: Path
    persona_text: str
    output_path: Path | None = None

    @property
    def skill_name(self) -> str:
        return self.skill_dir.name

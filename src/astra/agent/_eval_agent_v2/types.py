from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RepairTarget = Literal["none", "blueprint", "trajectory", "both"]


@dataclass(slots=True)
class EvalReview:
    summary: str
    strongest_positive: str
    strongest_negative: str
    root_causes: list[str] = field(default_factory=list)
    should_repair: bool = False
    repair_target: RepairTarget = "none"
    repair_strategy: str = ""
    export_training_artifact: bool = False


@dataclass(slots=True)
class RepairArtifacts:
    review: dict[str, Any] | None = None
    repair_report: dict[str, Any] | None = None
    training_export: dict[str, Any] | None = None

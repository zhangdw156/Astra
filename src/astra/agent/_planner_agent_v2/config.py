from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astra.utils import config as astra_config


@dataclass(frozen=True, slots=True)
class PlannerAgentV2Config:
    """
    PlannerAgentV2 的运行配置。
    """

    prompt_path: Path
    project_root: Path = astra_config.get_project_root()
    verbose: bool = False
    repair_attempts: int = 1

    def normalized(self) -> "PlannerAgentV2Config":
        return PlannerAgentV2Config(
            project_root=self.project_root.resolve(),
            prompt_path=self.prompt_path.resolve(),
            verbose=self.verbose,
            repair_attempts=self.repair_attempts,
        )

    def validate_basic(self) -> list[str]:
        errors: list[str] = []
        if self.repair_attempts < 0:
            errors.append(f"repair_attempts 不能小于 0: {self.repair_attempts}")
        return errors

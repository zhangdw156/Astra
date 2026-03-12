from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astra.utils import config as astra_config


@dataclass(frozen=True, slots=True)
class PlannerAgentConfig:
    """
    PlannerAgent 的运行配置。
    """

    prompt_path: Path
    project_root: Path = astra_config.get_project_root()
    model_temperature: float = 0.3
    verbose: bool = False

    def normalized(self) -> "PlannerAgentConfig":
        return PlannerAgentConfig(
            project_root=self.project_root.resolve(),
            prompt_path=self.prompt_path.resolve(),
            model_temperature=self.model_temperature,
            verbose=self.verbose,
        )

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if not (0.0 <= self.model_temperature <= 2.0):
            errors.append(
                f"model_temperature 必须在 [0.0, 2.0] 范围内: {self.model_temperature}"
            )

        return errors
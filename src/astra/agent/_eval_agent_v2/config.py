from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astra.utils import config as astra_config


@dataclass(frozen=True, slots=True)
class EvalAgentV2Config:
    """
    EvalAgentV2 的运行配置。
    """

    prompt_path: Path
    project_root: Path = astra_config.get_project_root()
    verbose: bool = False
    repair_attempts: int = 1
    max_message_chars: int | None = 4000
    write_review_artifact: bool = True
    export_repair_dataset_artifact: bool = True

    def normalized(self) -> "EvalAgentV2Config":
        return EvalAgentV2Config(
            prompt_path=self.prompt_path.resolve(),
            project_root=self.project_root.resolve(),
            verbose=self.verbose,
            repair_attempts=self.repair_attempts,
            max_message_chars=self.max_message_chars,
            write_review_artifact=self.write_review_artifact,
            export_repair_dataset_artifact=self.export_repair_dataset_artifact,
        )

    def validate_basic(self) -> list[str]:
        errors: list[str] = []
        if self.repair_attempts < 0:
            errors.append(f"repair_attempts 不能小于 0: {self.repair_attempts}")
        if self.max_message_chars is not None and self.max_message_chars <= 0:
            errors.append(
                f"max_message_chars 必须为正整数或 None: {self.max_message_chars}"
            )
        return errors

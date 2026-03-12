from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


SkillStatus = Literal["success", "skipped", "failed"]


@dataclass(slots=True)
class SkillProcessResult:
    """
    单个 skill 的处理结果。
    """

    skill_dir: Path
    status: SkillStatus
    exit_code: int = 0
    message: str = ""

    @property
    def skill_name(self) -> str:
        return self.skill_dir.name


@dataclass(slots=True)
class SkillRunSummary:
    """
    整体运行汇总。

    字段说明：
    - total_discovered: 发现的 skill 目录总数
    - attempted: 非 skipped 的处理数量
    - succeeded: 成功数量
    - skipped: 跳过数量
    - failed: 失败数量（包含预检查失败和执行失败）
    - results: 每个 skill 的处理结果
    """

    total_discovered: int = 0
    attempted: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    results: list[SkillProcessResult] = field(default_factory=list)

    @property
    def failed_names(self) -> list[str]:
        return [result.skill_name for result in self.results if result.status == "failed"]

    @property
    def succeeded_names(self) -> list[str]:
        return [result.skill_name for result in self.results if result.status == "success"]

    @property
    def skipped_names(self) -> list[str]:
        return [result.skill_name for result in self.results if result.status == "skipped"]
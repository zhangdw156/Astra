from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillAgentConfig:
    """
    SkillAgent 的运行配置。

    说明：
    - project_root: 项目根目录
    - skills_root: skills_demo 根目录
    - example_skill_dir: 参考示例 skill 目录
    - prompt_path: prompt 模板路径
    - dry_run: 只打印，不实际执行
    - skip_existing: 若已存在 tools.jsonl 则跳过
    - limit: 最多处理多少个 skill；0 表示不限制
    - verbose: 是否输出更详细日志，并让执行器继承终端输出
    """

    project_root: Path
    skills_root: Path
    example_skill_dir: Path
    prompt_path: Path

    dry_run: bool = False
    skip_existing: bool = False
    limit: int = 0
    verbose: bool = False

    def normalized(self) -> "SkillAgentConfig":
        """
        将所有路径标准化为绝对路径，返回一个新配置对象。
        """
        return SkillAgentConfig(
            project_root=self.project_root.resolve(),
            skills_root=self.skills_root.resolve(),
            example_skill_dir=self.example_skill_dir.resolve(),
            prompt_path=self.prompt_path.resolve(),
            dry_run=self.dry_run,
            skip_existing=self.skip_existing,
            limit=self.limit,
            verbose=self.verbose,
        )

    def validate_basic(self) -> list[str]:
        """
        只做不依赖文件系统存在性的轻量配置校验。
        """
        errors: list[str] = []

        if self.limit < 0:
            errors.append(f"limit 不能小于 0: {self.limit}")

        return errors
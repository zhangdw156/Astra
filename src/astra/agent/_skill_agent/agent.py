from __future__ import annotations

from pathlib import Path

from ...utils import logger

from .config import SkillAgentConfig
from .executor import OpenCodeExecutor, SubprocessOpenCodeExecutor
from .prompt_builder import PromptBuilder
from .types import SkillProcessResult, SkillRunSummary


class SkillAgent:
    """
    Skill 编排实体。

    职责：
    1. 校验环境
    2. 发现 skill 目录
    3. 决定是否跳过
    4. 构造 task text
    5. 调用 OpenCode
    6. 校验输出文件
    7. 汇总处理结果
    """

    def __init__(
        self,
        config: SkillAgentConfig,
        executor: OpenCodeExecutor | None = None,
    ):
        self.config = config.normalized()
        self.executor = executor or SubprocessOpenCodeExecutor()
        self.prompt_builder = PromptBuilder(self.config.prompt_path)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def run(self) -> tuple[int, SkillRunSummary]:
        """
        执行整个 skill 批处理流程。

        返回：
        - exit_code:
            0 -> 全部成功或被跳过
            1 -> 存在处理失败
            2 -> 运行环境错误
        - summary:
            整体处理汇总
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            for error in config_errors:
                logger.error(error)
            return 2, SkillRunSummary()

        env_errors = self.validate_environment()
        if env_errors:
            for error in env_errors:
                logger.error(error)
            return 2, SkillRunSummary()

        skill_dirs = self.discover_skills()
        summary = SkillRunSummary(total_discovered=len(skill_dirs))

        if not skill_dirs:
            logger.error("在目录下未发现任何 skill 子目录: {}", self.config.skills_root)
            return 2, summary

        self._log_header()

        processed_count = 0

        for index, skill_dir in enumerate(skill_dirs, start=1):
            if self.config.limit and processed_count >= self.config.limit:
                logger.info("已达到处理上限 {}，停止。", self.config.limit)
                break

            logger.info("[{}/{}] 处理 skill: {}", index, len(skill_dirs), skill_dir.name)

            result = self.process_skill(skill_dir)
            summary.results.append(result)

            if result.status == "success":
                summary.attempted += 1
                summary.succeeded += 1
                processed_count += 1
                logger.info("  SUCCESS: {}", result.message or result.skill_name)
                continue

            if result.status == "skipped":
                summary.skipped += 1
                logger.info("  SKIPPED: {}", result.message or result.skill_name)
                continue

            summary.attempted += 1
            summary.failed += 1
            processed_count += 1
            logger.error("  FAILED: {}", result.message or result.skill_name)

        self._log_summary(summary)

        exit_code = 1 if summary.failed > 0 else 0
        return exit_code, summary

    def discover_skills(self) -> list[Path]:
        """
        枚举 skills_root 下所有有效 skill 子目录。
        """
        root = self.config.skills_root
        if not root.exists():
            return []

        return [
            path
            for path in sorted(root.iterdir())
            if path.is_dir() and not path.name.startswith(".")
        ]

    def process_skill(self, skill_dir: Path) -> SkillProcessResult:
        """
        处理单个 skill 目录。
        """
        skill_errors = self.validate_skill_dir(skill_dir)
        if skill_errors:
            return SkillProcessResult(
                skill_dir=skill_dir,
                status="skipped",
                exit_code=0,
                message="; ".join(skill_errors),
            )

        tools_path = skill_dir / "tools.jsonl"

        if self.should_skip(skill_dir):
            return SkillProcessResult(
                skill_dir=skill_dir,
                status="skipped",
                exit_code=0,
                message=f"已存在 tools.jsonl: {tools_path}",
            )

        if self.config.dry_run:
            return SkillProcessResult(
                skill_dir=skill_dir,
                status="success",
                exit_code=0,
                message=f"DRY RUN: 将生成 {tools_path}",
            )

        task_text = self.build_task_text(skill_dir)
        exit_code = self.invoke_opencode(task_text)

        if exit_code != 0:
            return SkillProcessResult(
                skill_dir=skill_dir,
                status="failed",
                exit_code=exit_code,
                message=f"OpenCode 执行失败，exit code={exit_code}",
            )

        output_errors = self.validate_output(skill_dir)
        if output_errors:
            return SkillProcessResult(
                skill_dir=skill_dir,
                status="failed",
                exit_code=0,
                message="; ".join(output_errors),
            )

        return SkillProcessResult(
            skill_dir=skill_dir,
            status="success",
            exit_code=0,
            message=f"已生成 {tools_path}",
        )

    def should_skip(self, skill_dir: Path) -> bool:
        """
        判断当前 skill 是否应该跳过。
        """
        if not self.config.skip_existing:
            return False

        tools_path = skill_dir / "tools.jsonl"
        return tools_path.exists()

    def build_task_text(self, skill_dir: Path) -> str:
        """
        基于 prompt 模板和目录上下文构造 task text。
        """
        return self.prompt_builder.build(
            skill_dir=skill_dir,
            example_dir=self.config.example_skill_dir,
        )

    def invoke_opencode(self, task_text: str) -> int:
        """
        调用执行器运行 opencode。
        """
        logger.debug("Invoking: opencode run <task>")
        return self.executor.run(
            task_text=task_text,
            cwd=self.config.project_root,
            verbose=self.config.verbose,
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_environment(self) -> list[str]:
        """
        校验全局运行环境。
        这些检查只做一次，避免对每个 skill 重复执行。
        """
        errors: list[str] = []

        if not self.config.project_root.exists():
            errors.append(f"项目根目录不存在: {self.config.project_root}")

        if not self.config.skills_root.exists():
            errors.append(f"skills_root 不存在: {self.config.skills_root}")

        if not self.config.prompt_path.exists():
            errors.append(f"prompt 文件不存在: {self.config.prompt_path}")

        example_dir = self.config.example_skill_dir
        if not example_dir.exists():
            errors.append(f"示例目录不存在: {example_dir}")
            return errors

        example_skill_md = example_dir / "SKILL.md"
        example_tools_jsonl = example_dir / "tools.jsonl"

        if not example_skill_md.exists():
            errors.append(
                f"示例目录缺少 SKILL.md（必须始终参考 examples）: {example_dir}"
            )

        if not example_tools_jsonl.exists():
            errors.append(
                f"示例目录缺少 tools.jsonl（必须始终参考 examples）: {example_dir}"
            )

        return errors

    def validate_skill_dir(self, skill_dir: Path) -> list[str]:
        """
        校验单个 skill 目录的基本合法性。
        """
        errors: list[str] = []

        if not skill_dir.exists():
            errors.append(f"目录不存在: {skill_dir}")
            return errors

        if not skill_dir.is_dir():
            errors.append(f"不是目录: {skill_dir}")
            return errors

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"未找到 SKILL.md: {skill_md}")

        return errors

    def validate_output(self, skill_dir: Path) -> list[str]:
        """
        校验目标输出是否生成。
        当前只检查 tools.jsonl 是否存在、是否可读、是否非空。
        """
        errors: list[str] = []

        tools_path = skill_dir / "tools.jsonl"

        if not tools_path.exists():
            errors.append(f"tools.jsonl 未生成: {tools_path}")
            return errors

        if not tools_path.is_file():
            errors.append(f"tools.jsonl 不是普通文件: {tools_path}")
            return errors

        try:
            content = tools_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            errors.append(f"无法读取 tools.jsonl: {tools_path} ({exc})")
            return errors

        if not content:
            errors.append(f"tools.jsonl 为空文件: {tools_path}")

        return errors

    # -------------------------------------------------------------------------
    # Logging helpers
    # -------------------------------------------------------------------------

    def _log_header(self) -> None:
        logger.info("=" * 60)
        logger.info("SkillAgent: 批量生成 tools.jsonl")
        logger.info("=" * 60)
        logger.info("Project root:  {}", self.config.project_root)
        logger.info("Skills root:   {}", self.config.skills_root)
        logger.info("Example dir:   {}", self.config.example_skill_dir)
        logger.info("Prompt file:   {}", self.config.prompt_path)
        logger.info("Dry run:       {}", self.config.dry_run)
        logger.info("Skip existing: {}", self.config.skip_existing)
        logger.info("Limit:         {}", self.config.limit)
        logger.info("=" * 60)

    def _log_summary(self, summary: SkillRunSummary) -> None:
        logger.info("=" * 60)
        logger.info("完成")
        logger.info("发现 skill: {}", summary.total_discovered)
        logger.info("尝试处理:   {}", summary.attempted)
        logger.info("成功:       {}", summary.succeeded)
        logger.info("跳过:       {}", summary.skipped)
        logger.info("失败:       {}", summary.failed)

        if summary.failed_names:
            logger.info("失败的 skill: {}", ", ".join(summary.failed_names))

        logger.info("=" * 60)
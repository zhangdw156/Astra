#!/usr/bin/env python3
"""
pipeline2.py

作用：
- 指定一个 skills 根目录
- 使用当前 astra 的 SkillAgent，批量为其中所有 skill 目录生成 tools.jsonl

要求：
- 每个 skill 子目录至少应包含 SKILL.md
- 会使用一个示例 skill（example skill）和一份 prompt 模板驱动 SkillAgent
- 生成逻辑由 astra.agent._skill_agent 统一负责

典型用法：
uv run exps/data_synthesis_workflow/pipeline2.py \
  --skills-root /path/to/skills_demo \
  --example-skill-dir /path/to/examples/2896_prediction-trader \
  --prompt-path /path/to/prompts/skill_agent.md

可选：
uv run exps/data_synthesis_workflow/pipeline2.py \
  --skills-root /path/to/skills_demo \
  --example-skill-dir /path/to/examples/2896_prediction-trader \
  --prompt-path /path/to/prompts/skill_agent.md \
  --skip-existing \
  --limit 20 \
  --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from astra.agent._skill_agent import SkillAgent, SkillAgentConfig
from astra.utils import config as astra_config
from astra.utils import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 astra SkillAgent 批量为一个目录下的所有 skill 生成 tools.jsonl"
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        required=True,
        help="待处理的 skills 根目录，里面每个子目录视为一个 skill",
    )
    parser.add_argument(
        "--example-skill-dir",
        type=Path,
        required=True,
        help="参考示例 skill 目录（需包含 SKILL.md 与 tools.jsonl）",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        required=True,
        help="skill agent prompt 模板路径",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="项目根目录；默认使用 astra.utils.config.get_project_root()",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要处理的 skill，不实际调用 opencode",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若 skill 目录中已存在 tools.jsonl，则跳过",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多处理多少个 skill；0 表示不限制",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出更详细日志，并让 opencode 继承终端输出",
    )
    return parser.parse_args()


def resolve_path(path: Path, project_root: Path) -> Path:
    """
    若 path 是相对路径，则相对于 project_root 解析；否则直接 resolve。
    """
    if path.is_absolute():
        return path.resolve()
    return (project_root / path).resolve()


def main() -> int:
    args = parse_args()

    project_root = (
        args.project_root.resolve()
        if args.project_root is not None
        else astra_config.get_project_root().resolve()
    )

    skills_root = resolve_path(args.skills_root, project_root)
    example_skill_dir = resolve_path(args.example_skill_dir, project_root)
    prompt_path = resolve_path(args.prompt_path, project_root)

    logger.info("=" * 60)
    logger.info("Pipeline2: 基于 SkillAgent 批量生成 tools.jsonl")
    logger.info("=" * 60)
    logger.info("Project root:      {}", project_root)
    logger.info("Skills root:       {}", skills_root)
    logger.info("Example skill dir: {}", example_skill_dir)
    logger.info("Prompt path:       {}", prompt_path)
    logger.info("Dry run:           {}", args.dry_run)
    logger.info("Skip existing:     {}", args.skip_existing)
    logger.info("Limit:             {}", args.limit)
    logger.info("Verbose:           {}", args.verbose)
    logger.info("=" * 60)

    config = SkillAgentConfig(
        project_root=project_root,
        skills_root=skills_root,
        example_skill_dir=example_skill_dir,
        prompt_path=prompt_path,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
        limit=args.limit,
        verbose=args.verbose,
    )

    agent = SkillAgent(config=config)
    exit_code, summary = agent.run()

    logger.info("Pipeline2 finished with exit code={}", exit_code)
    logger.info(
        "Summary: discovered={}, attempted={}, succeeded={}, skipped={}, failed={}",
        summary.total_discovered,
        summary.attempted,
        summary.succeeded,
        summary.skipped,
        summary.failed,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
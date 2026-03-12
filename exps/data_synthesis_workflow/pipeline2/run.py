#!/usr/bin/env python3
"""
pipeline2：遍历 skills_demo 下的每个 skill 目录，调用本地 OpenCode CLI，
在 skill 目录内生成 tools.jsonl 文件。

特性与约束：
- 仅生成 tools.jsonl（不生成 MCP server、Docker 等），直接写入各 skill 目录。
- 参考示例固定为 examples/2896_prediction-trader（包含 SKILL.md 与 tools.jsonl）。
- 提示词来自本目录 prompts/skill_agent.md。
- 通过 opencode run <task> 调用 OpenCode，不复用 opencode_demo 下的代码实现。
- 代码仅依赖标准库、本目录以及 src/astra（当前未直接使用 astra）。

使用方式（在项目根目录执行）：
    uv run python exps/data-synthesis-workflow/pipeline2/run.py \\
        [--dry-run] [--limit N] [--skip-existing]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


# 路径：pipeline2/run.py -> exps -> 项目根
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# skills_demo 根目录与示例 skill 目录（始终参考 examples）
SKILLS_DEMO_DIR = PROJECT_ROOT / "skills_demo"
EXAMPLE_SKILL_DIR = PROJECT_ROOT / "examples" / "2896_prediction-trader"

# 提示词：指导 OpenCode 从 SKILL 目录生成 tools.jsonl
PROMPT_PATH = SCRIPT_DIR / "prompts" / "skill_agent.md"


def get_skill_dirs(root: Path) -> list[Path]:
    """获取 skills_demo 下所有有效 skill 子目录。"""
    if not root.exists():
        return []
    return [
        p
        for p in sorted(root.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


def build_task_text(skill_dir: Path, example_dir: Path, prompt_path: Path) -> str:
    """
    读取 skill_agent.md，将占位符替换为实际路径，构造传给 opencode run 的任务字符串。

    占位符：
    - {SKILL_DIR}: 目标 skill 目录
    - {EXAMPLE_DIR}: 参考示例目录（始终为 examples 下的示例）
    """
    prompt_text = prompt_path.read_text(encoding="utf-8")

    # 使用绝对路径，避免 cwd 变化导致歧义
    skill_abs = skill_dir.resolve()
    example_abs = example_dir.resolve()

    task_text = (
        prompt_text.replace("{SKILL_DIR}", str(skill_abs))
        .replace("{EXAMPLE_DIR}", str(example_abs))
    )
    return task_text


def run_opencode_for_skill(skill_dir: Path, example_dir: Path, prompt_path: Path) -> int:
    """
    针对单个 skill 目录调用 opencode run。
    返回 opencode 子进程的 exit code。
    """
    if not prompt_path.exists():
        print(f"ERROR: prompt 文件不存在: {prompt_path}", file=sys.stderr)
        return 2
    if not example_dir.exists():
        print(f"ERROR: 示例目录不存在: {example_dir}", file=sys.stderr)
        return 2
    if not (example_dir / "tools.jsonl").exists():
        print(
            f"ERROR: 示例目录缺少 tools.jsonl（必须始终参考 examples）: {example_dir}",
            file=sys.stderr,
        )
        return 2
    if not (example_dir / "SKILL.md").exists():
        print(
            f"ERROR: 示例目录缺少 SKILL.md（必须始终参考 examples）: {example_dir}",
            file=sys.stderr,
        )
        return 2

    if not (skill_dir / "SKILL.md").exists():
        print(f"  跳过：未找到 SKILL.md -> {skill_dir}", file=sys.stderr)
        return 0

    task_text = build_task_text(skill_dir, example_dir, prompt_path)

    print("=" * 60)
    print(f"OpenCode tools.jsonl 生成")
    print("=" * 60)
    print(f"Skill dir:   {skill_dir}")
    print(f"Example dir: {example_dir}")
    print("=" * 60)
    print("Invoking: opencode run <task>")
    print("=" * 60)

    # 使用项目根作为 cwd，便于 OpenCode 访问 examples / skills_demo 等目录
    result = subprocess.run(
        ["opencode", "run", task_text],
        cwd=PROJECT_ROOT,
        capture_output=False,
    )

    print("=" * 60)
    print(f"OpenCode exited with code: {result.returncode}")
    print("=" * 60)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "pipeline2: 遍历 skills_demo 下的 skill，"
            "使用 skill_agent.md 提示词指挥 OpenCode 为每个 skill 生成 tools.jsonl。"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要处理的 skill 目录，不实际调用 opencode。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多处理的 skill 数量（0 表示不限制）。",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若 skill 目录中已存在 tools.jsonl，则跳过该 skill。",
    )
    args = parser.parse_args()

    if not SKILLS_DEMO_DIR.exists():
        print(f"ERROR: skills_demo 目录不存在: {SKILLS_DEMO_DIR}", file=sys.stderr)
        return 2

    skill_dirs = get_skill_dirs(SKILLS_DEMO_DIR)
    if not skill_dirs:
        print(f"ERROR: 在 {SKILLS_DEMO_DIR} 下未找到任何 skill 目录", file=sys.stderr)
        return 2

    print("=" * 60)
    print("Pipeline2: 批量生成 tools.jsonl")
    print("=" * 60)
    print(f"Skills root:  {SKILLS_DEMO_DIR}")
    print(f"Example dir:  {EXAMPLE_SKILL_DIR}")
    print(f"Prompt file:  {PROMPT_PATH}")
    if args.limit:
        print(f"Limit:        {args.limit}")
    print(f"Skip existing: {args.skip_existing}")
    print("=" * 60)

    processed = 0
    failed: list[str] = []

    for idx, skill_dir in enumerate(skill_dirs, start=1):
        if args.limit and processed >= args.limit:
            print(f"\n已达到处理上限 {args.limit}，停止。")
            break

        tools_path = skill_dir / "tools.jsonl"
        print(f"\n[{idx}/{len(skill_dirs)}] 处理 skill: {skill_dir.name}")

        if args.skip_existing and tools_path.exists():
            print(f"  SKIP（已存在 tools.jsonl）: {tools_path}")
            continue

        if args.dry_run:
            print(f"  DRY RUN: 将为该目录生成 tools.jsonl -> {tools_path}")
            processed += 1
            continue

        code = run_opencode_for_skill(skill_dir, EXAMPLE_SKILL_DIR, PROMPT_PATH)
        if code == 0:
            processed += 1
        elif code == 0:
            # 已被上游逻辑视为“跳过而非错误”
            continue
        else:
            failed.append(skill_dir.name)

    print("\n" + "=" * 60)
    print(f"完成。成功处理: {processed}, 失败: {len(failed)}")
    if failed:
        print("失败的 skill:", ", ".join(failed))
    print("=" * 60)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())


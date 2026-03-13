#!/usr/bin/env python3
"""
基于 selected_skills.jsonl 批量为选中的 skill 生成 tools.jsonl。

设计目标：
- 输入不再是“遍历整个 skills_root”，而是“只处理 selected_skills.jsonl 中列出的 skill”
- 尽量贴近旧版 pipeline0 的行为：仍然通过 `opencode run <task>` 生成 tools.jsonl
- 支持并发、dry-run、skip-existing、limit

selected_skills.jsonl 每行至少应包含：
- dir_name

可选字段：
- skill_dir（若存在则优先使用）
- 其他字段会被忽略

使用方式示例：
    uv run exps/data_synthesis_workflow/pipeline0_selected_skills.py \
        --selected-skills artifacts/skill_manifest_top3.jsonl \
        --skills-root skills \
        --example-skill-dir examples/2896_prediction-trader \
        --prompt-path src/astra/prompts/skill_agent.md \
        --max-workers 1 \
        --skip-existing
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def load_selected_skills(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"selected_skills.jsonl 不存在: {path}")

    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"selected_skills.jsonl 第 {line_no} 行 JSON 非法: {e}"
                ) from e

            if not isinstance(obj, dict):
                raise ValueError(f"selected_skills.jsonl 第 {line_no} 行不是 JSON object")

            if "dir_name" not in obj and "skill_dir" not in obj:
                raise ValueError(
                    f"selected_skills.jsonl 第 {line_no} 行缺少 dir_name 或 skill_dir"
                )

            records.append(obj)

    return records


def resolve_skill_dir(record: dict[str, Any], skills_root: Path) -> Path:
    skill_dir = record.get("skill_dir")
    if isinstance(skill_dir, str) and skill_dir.strip():
        path = Path(skill_dir.strip())
        return path.resolve() if path.is_absolute() else (skills_root / path).resolve()

    dir_name = str(record.get("dir_name", "")).strip()
    if not dir_name:
        raise ValueError(f"record 缺少有效 dir_name: {record}")

    return (skills_root / dir_name).resolve()


def build_task_text(
    *,
    prompt_path: Path,
    skill_dir: Path,
    example_skill_dir: Path,
) -> str:
    prompt_text = prompt_path.read_text(encoding="utf-8")
    task_text = (
        prompt_text.replace("{SKILL_DIR}", str(skill_dir.resolve()))
        .replace("{EXAMPLE_DIR}", str(example_skill_dir.resolve()))
    )
    return task_text


def run_opencode_for_skill(
    *,
    project_root: Path,
    skill_dir: Path,
    example_skill_dir: Path,
    prompt_path: Path,
) -> int:
    if not prompt_path.exists():
        print(f"ERROR: prompt 文件不存在: {prompt_path}", file=sys.stderr)
        return 2

    if not example_skill_dir.exists():
        print(f"ERROR: 示例目录不存在: {example_skill_dir}", file=sys.stderr)
        return 2

    if not (example_skill_dir / "tools.jsonl").exists():
        print(
            f"ERROR: 示例目录缺少 tools.jsonl: {example_skill_dir}",
            file=sys.stderr,
        )
        return 2

    if not (example_skill_dir / "SKILL.md").exists():
        print(
            f"ERROR: 示例目录缺少 SKILL.md: {example_skill_dir}",
            file=sys.stderr,
        )
        return 2

    if not (skill_dir / "SKILL.md").exists():
        print(f"SKIP: 未找到 SKILL.md -> {skill_dir}", file=sys.stderr)
        return 0

    task_text = build_task_text(
        prompt_path=prompt_path,
        skill_dir=skill_dir,
        example_skill_dir=example_skill_dir,
    )

    result = subprocess.run(
        ["opencode", "run", task_text],
        cwd=project_root,
        capture_output=False,
    )
    return result.returncode


def worker(
    *,
    project_root: Path,
    record: dict[str, Any],
    skills_root: Path,
    example_skill_dir: Path,
    prompt_path: Path,
    skip_existing: bool,
    dry_run: bool,
) -> tuple[str, str, int]:
    """
    返回:
    - skill 标识
    - status: success / skipped / failed / dry-run
    - exit code
    """
    skill_dir = resolve_skill_dir(record, skills_root)
    skill_name = skill_dir.name
    tools_path = skill_dir / "tools.jsonl"

    if skip_existing and tools_path.exists():
        return skill_name, "skipped", 0

    if dry_run:
        return skill_name, "dry-run", 0

    code = run_opencode_for_skill(
        project_root=project_root,
        skill_dir=skill_dir,
        example_skill_dir=example_skill_dir,
        prompt_path=prompt_path,
    )
    if code == 0:
        return skill_name, "success", 0
    return skill_name, "failed", code


def infer_project_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists() or (parent / "src").exists():
            return parent
    return start.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="基于 selected_skills.jsonl 批量生成 tools.jsonl"
    )
    parser.add_argument(
        "--selected-skills",
        type=Path,
        required=True,
        help="selected_skills.jsonl 路径",
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        required=True,
        help="skill 根目录（若 selected record 未显式提供 skill_dir，则用 skills_root/dir_name 解析）",
    )
    parser.add_argument(
        "--example-skill-dir",
        type=Path,
        required=True,
        help="示例 skill 目录（应包含 SKILL.md 和 tools.jsonl）",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        required=True,
        help="skill agent 提示词模板路径",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="项目根目录；未指定则自动推断",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多处理多少个 skill（0 表示不限制）",
    )
    # TODO: 暂时不支持并发
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="并发 worker 数量",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="若 skill 目录中已存在 tools.jsonl，则跳过",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将处理哪些 skill，不实际调用 opencode",
    )

    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    project_root = (
        args.project_root.resolve()
        if args.project_root is not None
        else infer_project_root(script_path.parent)
    )
    selected_skills_path = args.selected_skills.resolve()
    skills_root = args.skills_root.resolve()
    example_skill_dir = args.example_skill_dir.resolve()
    prompt_path = args.prompt_path.resolve()

    records = load_selected_skills(selected_skills_path)
    if args.limit > 0:
        records = records[: args.limit]

    print("=" * 60)
    print("pipeline0 (selected skills): 生成 tools.jsonl")
    print("=" * 60)
    print(f"Selected skills: {selected_skills_path}")
    print(f"Skills root:     {skills_root}")
    print(f"Example skill:   {example_skill_dir}")
    print(f"Prompt path:     {prompt_path}")
    print(f"Project root:    {project_root}")
    print(f"Total selected:  {len(records)}")
    print(f"Max workers:     {args.max_workers}")
    print(f"Skip existing:   {args.skip_existing}")
    print(f"Dry run:         {args.dry_run}")
    print("=" * 60)

    succeeded = 0
    skipped = 0
    failed: list[str] = []
    dry_run_count = 0

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = [
            executor.submit(
                worker,
                project_root=project_root,
                record=record,
                skills_root=skills_root,
                example_skill_dir=example_skill_dir,
                prompt_path=prompt_path,
                skip_existing=args.skip_existing,
                dry_run=args.dry_run,
            )
            for record in records
        ]

        for future in as_completed(futures):
            skill_name, status, code = future.result()
            if status == "success":
                succeeded += 1
                print(f"[OK] {skill_name}")
            elif status == "skipped":
                skipped += 1
                print(f"[SKIP] {skill_name}")
            elif status == "dry-run":
                dry_run_count += 1
                print(f"[DRY-RUN] {skill_name}")
            else:
                failed.append(skill_name)
                print(f"[FAIL] {skill_name} (exit code={code})")

    print("\n" + "=" * 60)
    print("完成")
    print(f"成功: {succeeded}")
    print(f"跳过: {skipped}")
    print(f"Dry run: {dry_run_count}")
    print(f"失败: {len(failed)}")
    if failed:
        print("失败的 skill:", ", ".join(failed))
    print("=" * 60)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
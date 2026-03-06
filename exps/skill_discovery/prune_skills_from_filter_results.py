#!/usr/bin/env python3
"""
根据已有 filter result JSONL 文件，删除 skills 目录下 match=false 的 skill 子目录。

用于在日后根据 filter_domain_result.json 和 filter_executability_result.json
快速重新构建 skills 目录，无需重新调用 LLM 过滤。

数据格式：每行一个 JSON，含 dir_name、match、reason。match 为 false 时删除对应目录。

用法：
  uv run exps/skill_discovery/prune_skills_from_filter_results.py
  uv run exps/skill_discovery/prune_skills_from_filter_results.py --dry-run
  uv run exps/skill_discovery/prune_skills_from_filter_results.py --result-files a.json b.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _parse_result_file(path: Path) -> set[str]:
    """解析 JSONL 格式的 filter result，返回 match=false 的 dir_name 集合。"""
    to_delete: set[str] = set()
    if not path.exists():
        return to_delete
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            dir_name = obj.get("dir_name")
            match = obj.get("match")
            if dir_name is not None and match is False:
                to_delete.add(str(dir_name))
    return to_delete


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skills-dir",
        default="skills",
        help="待 pruning 的 skills 根目录（默认：skills）",
    )
    parser.add_argument(
        "--result-files",
        nargs="+",
        default=None,
        help="filter result JSONL 文件列表；不指定则使用 exps/skill_discovery/results 下默认两个",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印将要删除的目录，不实际删除",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    exps_skill = repo_root / "exps" / "skill_discovery"

    skills_dir = Path(args.skills_dir)
    if not skills_dir.is_absolute():
        skills_dir = (repo_root / skills_dir).resolve()

    if args.result_files:
        result_paths = [Path(p) for p in args.result_files]
    else:
        result_paths = [
            exps_skill / "results" / "filter_domain_result.json",
            exps_skill / "results" / "filter_executability_result.json",
        ]

    to_delete: set[str] = set()
    for rp in result_paths:
        rp = Path(rp)
        if not rp.is_absolute():
            rp = repo_root / rp
        if not rp.exists():
            print(f"跳过不存在的文件: {rp}", file=sys.stderr)
            continue
        parsed = _parse_result_file(rp)
        to_delete |= parsed
        print(f"从 {rp.name} 解析到 {len(parsed)} 个 match=false 的 dir_name")

    print(f"\n合计需删除 {len(to_delete)} 个目录（match=false）")

    if not skills_dir.is_dir():
        print(f"skills_dir 不存在或不是目录: {skills_dir}", file=sys.stderr)
        return 1

    deleted = 0
    skipped = 0
    for dir_name in sorted(to_delete):
        target = skills_dir / dir_name
        if not target.exists():
            skipped += 1
            if args.dry_run:
                print(f"[跳过-不存在] {dir_name}")
            continue
        if not target.is_dir():
            skipped += 1
            if args.dry_run:
                print(f"[跳过-非目录] {dir_name}")
            continue
        print(f"{'[dry-run] ' if args.dry_run else ''}删除: {target}")
        if not args.dry_run:
            shutil.rmtree(target)
        deleted += 1

    print(f"\n完成。删除 {deleted} 个，跳过 {skipped} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

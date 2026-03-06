#!/usr/bin/env python3
"""
确保 skills_demo 目录下有足够数量的 skill 目录。

逻辑：
- 统计 skills_demo 下的一级子目录数量
- 若不足 target_count，则从 skills_dir 下随机抽取缺口数量的子目录，复制到 skills_demo 下
- 若同名目录已存在则跳过，直到补齐或候选耗尽

用法：
  uv run exps/skill_discovery/ensure_skills_demo.py
  uv run exps/skill_discovery/ensure_skills_demo.py --target-count 25 --seed 42
  uv run exps/skill_discovery/ensure_skills_demo.py --dry-run
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path


def _list_subdirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    return sorted([p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skills-dir", default="skills", help="源 skills 目录（默认：skills）")
    parser.add_argument("--skills-demo-dir", default="skills_demo", help="目标演示目录（默认：skills_demo）")
    parser.add_argument("--target-count", type=int, default=25, help="目标子目录数量（默认：25）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认：不固定）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印计划，不实际复制")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    skills_dir = Path(args.skills_dir)
    skills_demo_dir = Path(args.skills_demo_dir)
    if not skills_dir.is_absolute():
        skills_dir = (repo_root / skills_dir).resolve()
    if not skills_demo_dir.is_absolute():
        skills_demo_dir = (repo_root / skills_demo_dir).resolve()

    if args.target_count <= 0:
        print("--target-count 必须为正整数", file=sys.stderr)
        return 2

    if not skills_dir.is_dir():
        print(f"skills_dir 不存在或不是目录: {skills_dir}", file=sys.stderr)
        return 1

    skills_demo_dir.mkdir(parents=True, exist_ok=True)

    existing = _list_subdirs(skills_demo_dir)
    existing_names = {p.name for p in existing}
    current = len(existing_names)
    print(f"skills_demo 当前数量: {current} (目录: {skills_demo_dir})")

    if current >= args.target_count:
        print("数量已满足，无需复制。")
        return 0

    need = args.target_count - current
    candidates = [p for p in _list_subdirs(skills_dir) if p.name not in existing_names]
    if not candidates:
        print("无可复制候选（skills 中目录都已存在于 skills_demo 或 skills 为空）。", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    rng.shuffle(candidates)

    picked: list[Path] = []
    for p in candidates:
        if len(picked) >= need:
            break
        picked.append(p)

    if len(picked) < need:
        print(f"候选不足：需要 {need} 个，但只能提供 {len(picked)} 个。将复制可用的部分。", file=sys.stderr)

    for src in picked:
        dst = skills_demo_dir / src.name
        if dst.exists():
            continue
        print(f"复制: {src} -> {dst}")
        if not args.dry_run:
            shutil.copytree(src, dst)

    print("完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


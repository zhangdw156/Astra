"""
循环调用 run_opencode_env_gen，对 skills_demo 下的每个 skill 在 env_demo 中生成对应的 MCP 环境。

前置条件：本地已安装 opencode CLI，完成 opencode auth login。
运行方式：python exps/data-synthesis-workflow/opencode_demo/batch_env_gen.py [--dry-run] [--limit N] [--skip-existing]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 脚本与路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent

SKILLS_DEMO_DIR = PROJECT_ROOT / "skills_demo"
ENV_DEMO_DIR = PROJECT_ROOT / "env_demo"
RUN_SCRIPT = SCRIPT_DIR / "run_opencode_env_gen.py"


def get_skill_dirs() -> list[Path]:
    """获取 skills_demo 下所有 skill 子目录"""
    if not SKILLS_DEMO_DIR.exists():
        return []
    return [
        p
        for p in sorted(SKILLS_DEMO_DIR.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Batch generate MCP env for all skills in skills_demo, output to env_demo."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list skills and target env dirs, do not run opencode",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max number of skills to process (0 = no limit)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip skill if corresponding env dir already exists with mcp_server.py",
    )
    parser.add_argument(
        "--ref-skill-dir",
        type=Path,
        default=SCRIPT_DIR / "2896_prediction-trader",
        help="Reference skill dir",
    )
    parser.add_argument(
        "--ref-env-dir",
        type=Path,
        default=SCRIPT_DIR / "env_2896_prediction-trader",
        help="Reference env dir",
    )
    parser.add_argument(
        "--validate-script",
        type=Path,
        default=None,
        help="Optional path to single-env validation script (forwarded to run_opencode_env_gen.py)",
    )
    args = parser.parse_args()

    skill_dirs = get_skill_dirs()
    if not skill_dirs:
        print(f"No skills found in {SKILLS_DEMO_DIR}")
        return 1

    ENV_DEMO_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Batch OpenCode Environment Generation")
    print("=" * 60)
    print(f"Skills dir: {SKILLS_DEMO_DIR}")
    print(f"Env output: {ENV_DEMO_DIR}")
    print(f"Total skills: {len(skill_dirs)}")
    if args.limit:
        print(f"Limit: {args.limit}")
    print("=" * 60)

    processed = 0
    failed = []

    for i, skill_dir in enumerate(skill_dirs):
        if args.limit and processed >= args.limit:
            print(f"\nReached limit {args.limit}, stopping.")
            break

        env_name = f"env_{skill_dir.name}"
        env_dir = ENV_DEMO_DIR / env_name

        if args.skip_existing and (env_dir / "mcp_server.py").exists():
            print(f"[{i+1}/{len(skill_dirs)}] SKIP (exists): {skill_dir.name} -> {env_name}")
            continue

        print(f"\n[{i+1}/{len(skill_dirs)}] {skill_dir.name} -> {env_name}")

        if args.dry_run:
            print(f"  Would run: opencode run ...")
            processed += 1
            continue

        cmd = [
            sys.executable,
            str(RUN_SCRIPT),
            "--ref-skill-dir",
            str(args.ref_skill_dir),
            "--ref-env-dir",
            str(args.ref_env_dir),
            "--skill-dir",
            str(skill_dir),
            "--env-dir",
            str(env_dir),
        ]
        if args.validate_script is not None:
            cmd.extend(["--validate-script", str(args.validate_script.resolve())])

        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

        if result.returncode == 0:
            print(f"  OK: {env_name}")
            processed += 1
        else:
            print(f"  FAILED (exit {result.returncode}): {skill_dir.name}")
            failed.append(skill_dir.name)

    print("\n" + "=" * 60)
    print(f"Done. Processed: {processed}, Failed: {len(failed)}")
    if failed:
        print("Failed skills:", ", ".join(failed))
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

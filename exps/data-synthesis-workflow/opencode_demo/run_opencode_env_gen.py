"""
使用 prompts/skill_to_environment.md 提示词，通过 subprocess 调用本地 OpenCode CLI 的 run 命令，
从 skill 目录生成可运行的 MCP 环境目录。

前置条件：本地已安装 opencode CLI（opencode --version 可验证），并完成 opencode auth login。
运行方式：python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py [--skill-dir PATH] [--env-dir PATH]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 脚本与 workflow 目录
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROMPT_PATH = WORKFLOW_DIR / "prompts" / "skill_to_environment.md"

DEFAULT_SKILL_DIR = WORKFLOW_DIR / "2896_prediction-trader"
DEFAULT_ENV_DIR = WORKFLOW_DIR / "env_2896_prediction-trader"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call OpenCode run to generate MCP environment from skill dir using skill_to_environment prompt."
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=DEFAULT_SKILL_DIR,
        help=f"Skill directory (default: {DEFAULT_SKILL_DIR})",
    )
    parser.add_argument(
        "--env-dir",
        type=Path,
        default=DEFAULT_ENV_DIR,
        help=f"Target environment directory to generate (default: {DEFAULT_ENV_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_dir = args.skill_dir.resolve()
    env_dir = args.env_dir.resolve()

    if not PROMPT_PATH.exists():
        print(f"Error: Prompt file not found: {PROMPT_PATH}")
        return 1

    if not skill_dir.exists():
        print(f"Error: Skill directory not found: {skill_dir}")
        return 1

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_text.replace("{SKILL_DIR}", str(skill_dir))
    prompt_text = prompt_text.replace("{ENV_DIR}", str(env_dir))

    task_prefix = (
        "Generate an MCP environment from the skill directory. "
        f"Follow the instructions below.\n\n"
        f"Skill dir: {skill_dir}\n"
        f"Target env dir: {env_dir}\n\n"
        "---\n\n"
    )
    task_text = task_prefix + prompt_text

    cwd = env_dir.parent

    print("=" * 60)
    print("OpenCode Environment Generation Demo")
    print("=" * 60)
    print(f"Skill dir:  {skill_dir}")
    print(f"Env dir:    {env_dir}")
    print(f"Prompt:     {PROMPT_PATH}")
    print(f"Working dir: {cwd}")
    print("=" * 60)
    print("Invoking: opencode run <task>")
    print("=" * 60)

    result = subprocess.run(
        ["opencode", "run", task_text],
        cwd=cwd,
        capture_output=False,
    )

    print("=" * 60)
    print(f"OpenCode exited with code: {result.returncode}")
    print("=" * 60)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

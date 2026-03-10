"""
使用 prompts/skill_to_environment.md 提示词，通过 subprocess 调用本地 OpenCode CLI 的 run 命令，
从 skill 目录生成可运行的 MCP 环境目录。

前置条件：本地已安装 opencode CLI（opencode --version 可验证），并完成 opencode auth login。
运行方式：python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py [options]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# 脚本、workflow、项目根目录
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent
PROMPT_PATH = WORKFLOW_DIR / "prompts" / "skill_to_environment.md"

# 参考示例：生成前后的目录对（OpenCode 需先阅读此对以学习模式）
DEFAULT_REF_SKILL_DIR = SCRIPT_DIR / "2896_prediction-trader"
DEFAULT_REF_ENV_DIR = SCRIPT_DIR / "env_2896_prediction-trader"

# 默认生成目标：skill 输入与环境输出
DEFAULT_SKILL_DIR = PROJECT_ROOT / "skills_demo" / "2515_stock-monitor"
DEFAULT_ENV_DIR = WORKFLOW_DIR / "env_2515_stock-monitor"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call OpenCode run to generate MCP environment from skill dir using skill_to_environment prompt."
    )
    parser.add_argument(
        "--ref-skill-dir",
        type=Path,
        default=DEFAULT_REF_SKILL_DIR,
        help=f"Reference skill dir to study (default: {DEFAULT_REF_SKILL_DIR})",
    )
    parser.add_argument(
        "--ref-env-dir",
        type=Path,
        default=DEFAULT_REF_ENV_DIR,
        help=f"Reference env dir to study (default: {DEFAULT_REF_ENV_DIR})",
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=DEFAULT_SKILL_DIR,
        help=f"Skill directory to transform (default: {DEFAULT_SKILL_DIR})",
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
    ref_skill_dir = args.ref_skill_dir.resolve()
    ref_env_dir = args.ref_env_dir.resolve()
    skill_dir = args.skill_dir.resolve()
    env_dir = args.env_dir.resolve()

    if not PROMPT_PATH.exists():
        print(f"Error: Prompt file not found: {PROMPT_PATH}")
        return 1

    if not ref_skill_dir.exists():
        print(f"Error: Reference skill dir not found: {ref_skill_dir}")
        return 1
    if not ref_env_dir.exists():
        print(f"Error: Reference env dir not found: {ref_env_dir}")
        return 1
    if not skill_dir.exists():
        print(f"Error: Skill directory not found: {skill_dir}")
        return 1

    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_text.replace("{REF_SKILL_DIR}", str(ref_skill_dir))
    prompt_text = prompt_text.replace("{REF_ENV_DIR}", str(ref_env_dir))
    prompt_text = prompt_text.replace("{SKILL_DIR}", str(skill_dir))
    prompt_text = prompt_text.replace("{ENV_DIR}", str(env_dir))

    task_prefix = (
        "STEP 1 — Read the reference example pair first:\n"
        f"- Read skill dir: {ref_skill_dir}\n"
        f"- Read env dir: {ref_env_dir}\n"
        "Study mcp_server.py (dynamic discovery), a tool file, Dockerfile, docker-compose, and a mock.\n\n"
        "STEP 2 — Generate:\n"
        f"- Input skill: {skill_dir}\n"
        f"- Output env: {env_dir}\n"
        "Create the environment at the output path, replicating the patterns from the reference.\n\n"
        "STEP 3 — Validate (required): After generation, run:\n"
        f"  uv run python exps/data-synthesis-workflow/opencode_demo/validate_env.py {env_dir}\n"
        "Fix any validation failures and re-run until exit code 0. Do not finish until validation passes.\n\n"
        "---\n\n"
    )
    task_text = task_prefix + prompt_text

    # 使用项目根作为 cwd，便于 OpenCode 访问参考目录和 skills_demo
    cwd = PROJECT_ROOT

    print("=" * 60)
    print("OpenCode Environment Generation Demo")
    print("=" * 60)
    print(f"Ref skill:  {ref_skill_dir}")
    print(f"Ref env:    {ref_env_dir}")
    print(f"Skill dir:  {skill_dir}")
    print(f"Env dir:    {env_dir}")
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

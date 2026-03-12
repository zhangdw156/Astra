#!/usr/bin/env python3
"""
pipeline1 多 skill 合成脚本：

- 从 skills_demo 中筛选出已生成 tools.jsonl 的 skill 目录（期望 25 个）。
- 从 persona_5K.jsonl 中全局抽取不重复的 persona，总计 N_skill * num_per_skill 条。
- 对每个 skill：
  - 使用该 skill 的 tools.jsonl 启动轻量 MCP Server（astra run_light_mcp），在本 skill 的 20 条实验中复用。
  - 对每个 persona：
    - 生成蓝图（run_blueprint.py）。
    - 基于当前 MCP Server 生成轨迹（run_simulation.py，使用 --mcp-url）。
    - 对轨迹做评估（run_evaluation.py）。
- 轨迹中 tools 字段已在 run_simulation.py 中改为优先写入完整 tools.jsonl 内容。

运行方式（项目根目录）：
  uv run python exps/data-synthesis-workflow/pipeline1/run_multi_skill.py
"""

from __future__ import annotations

import argparse
import atexit
import concurrent.futures
import json
import random
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path


# 路径：pipeline1/run_multi_skill.py -> exps -> 项目根
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

SCRIPTS_DIR = SCRIPT_DIR / "scripts"
PERSONA_PATH_DEFAULT = SCRIPT_DIR / "data" / "persona_5K.jsonl"
SKILLS_ROOT_DEFAULT = PROJECT_ROOT / "skills_demo"

ARTIFACTS_MULTI_ROOT = SCRIPT_DIR / "artifacts_multi"

# MCP SSE 端点（与 run_simulation / run.py 保持一致）
MCP_SSE_URL = "http://localhost:8000/sse"

_light_mcp_proc: subprocess.Popen | None = None


def _mcp_reachable(url: str = MCP_SSE_URL) -> bool:
    """检查 MCP SSE 端点是否可连接。"""
    try:
        from urllib.request import urlopen

        with urlopen(url, timeout=3):
            return True
    except Exception:
        return False


@contextmanager
def start_light_mcp_subprocess(tools_path: Path) -> None:
    """
    通过 astra run_light_mcp 子进程启动 MCP（SSE），就绪后 yield，退出时终止子进程。
    针对单个 skill 复用 MCP：在 with 作用域内生成多条轨迹。
    """
    global _light_mcp_proc
    tools_abs = tools_path.resolve() if not tools_path.is_absolute() else tools_path
    if not tools_abs.exists():
        raise FileNotFoundError(f"tools_path 不存在: {tools_abs}")

    prompt_path = SCRIPT_DIR / "prompts" / "tool_agent.md"
    prompt_abs = prompt_path.resolve() if not prompt_path.is_absolute() else prompt_path

    cmd = [
        "uv",
        "run",
        "-m",
        "astra.scripts.run_light_mcp",
        f"tools_path={tools_abs}",
        f"prompt_path={prompt_abs}",
        "transport=sse",
    ]
    print("正在启动轻量 MCP 子进程:", " ".join(cmd))
    _light_mcp_proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    atexit.register(
        lambda: _light_mcp_proc
        and _light_mcp_proc.poll() is None
        and _light_mcp_proc.terminate()
    )

    max_wait = 60
    interval = 2
    elapsed = 0
    while elapsed < max_wait:
        if _light_mcp_proc.poll() is not None:
            raise RuntimeError("轻量 MCP 子进程已退出")
        time.sleep(interval)
        elapsed += interval
        if _mcp_reachable():
            print(f"MCP 子进程已就绪（约 {elapsed}s）")
            try:
                yield
            finally:
                if _light_mcp_proc and _light_mcp_proc.poll() is None:
                    _light_mcp_proc.terminate()
                    _light_mcp_proc.wait(timeout=5)
                _light_mcp_proc = None
            return

    _light_mcp_proc.terminate()
    _light_mcp_proc.wait(timeout=5)
    _light_mcp_proc = None
    raise RuntimeError("MCP 子进程启动超时，SSE 未就绪")


def load_personas(path: Path) -> list[str]:
    """读取 persona JSONL，每行一条，返回行列表。"""
    if not path.exists():
        raise FileNotFoundError(f"persona 文件不存在: {path}")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return lines


def pick_skills_with_tools(skills_root: Path) -> list[Path]:
    """
    从 skills_root 中选择包含 tools.jsonl 的 skill 目录。
    期望数量为 25，若数量不足则抛出错误。
    """
    if not skills_root.exists():
        raise FileNotFoundError(f"skills_root 不存在: {skills_root}")
    skills: list[Path] = []
    for p in sorted(skills_root.iterdir()):
        if p.is_dir() and not p.name.startswith(".") and (p / "tools.jsonl").exists():
            skills.append(p)
    return skills


def assign_personas_to_skills(
    personas: list[str],
    skills: list[Path],
    num_per_skill: int,
    rng: random.Random,
) -> dict[str, list[int]]:
    """
    为每个 skill 分配 num_per_skill 个 persona 索引，保证全局不重复。
    返回映射：skill_name -> persona 索引列表。
    """
    total_needed = len(skills) * num_per_skill
    if len(personas) < total_needed:
        raise ValueError(
            f"persona 数量不足：需要 {total_needed} 条，但仅有 {len(personas)} 条"
        )

    indices = list(range(len(personas)))
    rng.shuffle(indices)
    selected = indices[:total_needed]

    mapping: dict[str, list[int]] = {}
    for i, skill_dir in enumerate(skills):
        start = i * num_per_skill
        end = start + num_per_skill
        mapping[skill_dir.name] = selected[start:end]
    return mapping


def run_blueprint(persona_line: str, out_blueprint: Path, skill_name: str, skill_dir: Path) -> bool:
    """
    生成单个蓝图，附带 skill_name 字段，便于后续轨迹标记。
    """
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_blueprint.py"),
        "--persona",
        persona_line.strip(),
        "--skill-dir",
        str(skill_dir),
        "--output",
        str(out_blueprint),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if r.returncode != 0:
        return False

    try:
        data = json.loads(out_blueprint.read_text(encoding="utf-8"))
        data["skill_name"] = skill_name
        out_blueprint.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"  警告：更新蓝图 skill_name 时出错: {e}")
    return True


def run_agent(
    blueprint_path: Path,
    out_trajectory: Path,
    run_id: str,
    mcp_url: str,
) -> bool:
    """
    调用 run_simulation.py，传入 --mcp-url 复用当前 MCP Server。
    """
    out_trajectory.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_simulation.py"),
        "--blueprint",
        str(blueprint_path),
        "--mcp-url",
        mcp_url,
        "--output",
        str(out_trajectory),
        "--run-id",
        run_id,
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def run_eval(trajectory_path: Path, out_eval: Path) -> bool:
    """调用 run_evaluation.py，输出评估到 out_eval。"""
    out_eval.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_evaluation.py"),
        "--trajectory",
        str(trajectory_path),
        "--output",
        str(out_eval),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def run_one_sample_for_skill(
    *,
    skill_name: str,
    skill_dir: Path,
    skill_artifacts_root: Path,
    sample_index: int,
    persona_idx: int,
    persona_line: str,
    mcp_url: str,
) -> tuple[bool, bool, bool]:
    """
    在单个 skill 下执行一条样本的 蓝图->轨迹->评估 流程。
    返回 (blueprint_ok, trajectory_ok, eval_ok)。
    """
    run_local_id = f"multi_{skill_name}_{sample_index}"

    print("\n" + "-" * 60)
    print(
        f"[{skill_name}] 样本 {sample_index + 1} "
        f"(persona_idx={persona_idx})"
    )
    print("-" * 60)

    run_dir = skill_artifacts_root / str(sample_index)
    run_dir.mkdir(parents=True, exist_ok=True)

    blueprint_path = run_dir / "blueprint.json"
    blueprint_ok = run_blueprint(persona_line, blueprint_path, skill_name, skill_dir)
    if not blueprint_ok:
        print(f"  [{skill_name}#{sample_index}] 蓝图生成失败")
        return False, False, False

    traj_path = run_dir / "trajectory.json"
    trajectory_ok = run_agent(blueprint_path, traj_path, run_local_id, mcp_url)
    if not trajectory_ok:
        print(f"  [{skill_name}#{sample_index}] 轨迹生成失败")
        return True, False, False

    eval_path = run_dir / "evaluation.json"
    eval_ok = run_eval(traj_path, eval_path)
    if not eval_ok:
        print(f"  [{skill_name}#{sample_index}] 评估失败")
    return True, True, eval_ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "pipeline1 多 skill 合成脚本：基于 skills_demo 中带 tools.jsonl 的 skill，"
            "为每个 skill 生成多条蓝图+轨迹+评估，persona 全局不重复。"
        )
    )
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=SKILLS_ROOT_DEFAULT,
        help=f"skills_demo 根目录（默认: {SKILLS_ROOT_DEFAULT}）",
    )
    parser.add_argument(
        "--persona-path",
        type=Path,
        default=PERSONA_PATH_DEFAULT,
        help=f"persona JSONL 文件路径（默认: {PERSONA_PATH_DEFAULT}）",
    )
    parser.add_argument(
        "--num-per-skill",
        type=int,
        default=20,
        help="每个 skill 要生成的样本数（默认 20）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="随机种子（可选，用于 persona 分配的可重复性）",
    )
    parser.add_argument(
        "--workers-per-skill",
        type=int,
        default=1,
        help="每个 skill 内并发生成样本的 worker 数（默认 1，即串行）",
    )
    args = parser.parse_args()
    if args.workers_per_skill < 1:
        raise SystemExit("--workers-per-skill 必须 >= 1")

    rng = random.Random(args.seed)

    personas = load_personas(args.persona_path)
    skills = pick_skills_with_tools(args.skills_root)

    print("=" * 60)
    print("pipeline1 多 skill 合成配置")
    print("=" * 60)
    print(f"Skills root:      {args.skills_root}")
    print(f"Persona path:     {args.persona_path}")
    print(f"技能数（含 tools.jsonl）: {len(skills)}")
    print(f"每个 skill 样本数: {args.num_per_skill}")
    print(f"每个 skill 并发数: {args.workers_per_skill}")
    print(f"persona 总数:     {len(personas)}")
    print("=" * 60)

    if not skills:
        print("ERROR: 未在 skills_root 中找到任何包含 tools.jsonl 的 skill 目录", file=sys.stderr)
        return 2

    total_needed = len(skills) * args.num_per_skill
    if len(personas) < total_needed:
        print(
            f"ERROR: persona 数量不足，生成 {len(skills)} * {args.num_per_skill} = {total_needed} "
            f"条数据时，至少需要同等数量 persona（当前 {len(personas)}）",
            file=sys.stderr,
        )
        return 2

    persona_assignments = assign_personas_to_skills(
        personas, skills, args.num_per_skill, rng
    )

    ARTIFACTS_MULTI_ROOT.mkdir(parents=True, exist_ok=True)

    total_blueprints = 0
    total_trajectories = 0
    total_evals = 0

    for skill_dir in skills:
        skill_name = skill_dir.name
        tools_path = skill_dir / "tools.jsonl"
        persona_indices = persona_assignments.get(skill_name, [])

        print("\n" + "=" * 60)
        print(f"Skill: {skill_name}")
        print(f"tools.jsonl: {tools_path}")
        print(f"分配 persona 数: {len(persona_indices)}")
        print("=" * 60)

        if not persona_indices:
            print(f"  跳过：未为 {skill_name} 分配 persona")
            continue

        skill_artifacts_root = ARTIFACTS_MULTI_ROOT / skill_name
        skill_artifacts_root.mkdir(parents=True, exist_ok=True)

        try:
            with start_light_mcp_subprocess(tools_path):
                print(f"\nMCP Server 已就绪（skill={skill_name}），开始合成该 skill 的样本...")
                sample_tasks = [
                    (j, persona_idx, personas[persona_idx])
                    for j, persona_idx in enumerate(persona_indices)
                ]

                if args.workers_per_skill == 1:
                    for j, persona_idx, persona_line in sample_tasks:
                        bp_ok, tr_ok, ev_ok = run_one_sample_for_skill(
                            skill_name=skill_name,
                            skill_dir=skill_dir,
                            skill_artifacts_root=skill_artifacts_root,
                            sample_index=j,
                            persona_idx=persona_idx,
                            persona_line=persona_line,
                            mcp_url=MCP_SSE_URL,
                        )
                        total_blueprints += int(bp_ok)
                        total_trajectories += int(tr_ok)
                        total_evals += int(ev_ok)
                else:
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=args.workers_per_skill
                    ) as executor:
                        futures = [
                            executor.submit(
                                run_one_sample_for_skill,
                                skill_name=skill_name,
                                skill_dir=skill_dir,
                                skill_artifacts_root=skill_artifacts_root,
                                sample_index=j,
                                persona_idx=persona_idx,
                                persona_line=persona_line,
                                mcp_url=MCP_SSE_URL,
                            )
                            for j, persona_idx, persona_line in sample_tasks
                        ]
                        for fut in concurrent.futures.as_completed(futures):
                            bp_ok, tr_ok, ev_ok = fut.result()
                            total_blueprints += int(bp_ok)
                            total_trajectories += int(tr_ok)
                            total_evals += int(ev_ok)

        except Exception as e:
            print(f"ERROR: skill {skill_name} 合成过程中发生异常: {e}", file=sys.stderr)
            continue

    print("\n" + "=" * 60)
    print("pipeline1 多 skill 合成完成")
    print(f"  蓝图: {total_blueprints}")
    print(f"  轨迹: {total_trajectories}")
    print(f"  评估: {total_evals}")
    print(f"  期望样本总数: {len(skills) * args.num_per_skill}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

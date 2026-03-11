#!/usr/bin/env python3
"""
pipeline1：从 persona_5K.jsonl 随机抽 20 个人物，生成 20 蓝图、采集 20 轨迹并做评估。

依赖：blueprint_demo、agent_demo、trajectory_eval_demo、prompts、env_2896_prediction-trader/tools.jsonl。
请在项目根目录执行：python exps/data-synthesis-workflow/pipeline1/run.py [--num 20] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

# 路径：pipeline1/run.py -> workflow -> exps -> 项目根
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent

PERSONA_PATH = PROJECT_ROOT / "persona" / "persona_5K.jsonl"
TOOLS_PATH = WORKFLOW_DIR / "opencode_demo" / "env_2896_prediction-trader" / "tools.jsonl"
BLUEPRINT_DEMO = WORKFLOW_DIR / "blueprint_demo"
AGENT_DEMO = WORKFLOW_DIR / "agent_demo"
EVAL_DEMO = WORKFLOW_DIR / "trajectory_eval_demo"

OUT_BLUEPRINTS = SCRIPT_DIR / "blueprints"
OUT_TRAJECTORIES = SCRIPT_DIR / "trajectories"
OUT_EVALS = SCRIPT_DIR / "evals"
SCRATCH = SCRIPT_DIR / "scratch"


def load_personas(path: Path) -> list[str]:
    """读取 persona JSONL，每行一条，返回行列表。"""
    if not path.exists():
        raise FileNotFoundError(f"persona 文件不存在: {path}")
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return lines


def messages_to_turns(messages: list[dict]) -> list[dict]:
    """
    将 agent_demo 保存的 messages（role/content）转为 trajectory_eval 所需的 turns。
    每轮：一个 user + 紧随的 assistant（及 function）合并为一个 turn。
    """
    turns: list[dict] = []
    i = 0
    while i < len(messages):
        m = messages[i]
        role = m.get("role", "")
        if role != "user":
            i += 1
            continue
        user_message = (m.get("content") or "").strip()
        assistant_message = ""
        tool_calls: list[dict] = []
        j = i + 1
        while j < len(messages):
            next_m = messages[j]
            next_role = next_m.get("role", "")
            if next_role == "user":
                break
            if next_role == "assistant":
                assistant_message = (next_m.get("content") or "").strip()
                # 若同一轮有 function_call，在后续 function 里补 result
                j += 1
                continue
            if next_role == "function":
                tool_calls.append({
                    "name": next_m.get("name", ""),
                    "arguments": "",
                    "result": (next_m.get("content") or "")[:500],
                })
                j += 1
                continue
            j += 1
        turns.append({
            "turn_index": len(turns) + 1,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "tool_calls": tool_calls,
        })
        i = j
    return turns


def run_blueprint(persona_line: str, out_blueprint: Path, scratch_dir: Path) -> bool:
    """写单行 persona 到临时文件，调用 run_blueprint.py，输出到 out_blueprint。"""
    scratch_dir.mkdir(parents=True, exist_ok=True)
    persona_file = scratch_dir / "persona_current.jsonl"
    persona_file.write_text(persona_line.strip() + "\n", encoding="utf-8")

    cmd = [
        sys.executable,
        str(BLUEPRINT_DEMO / "run_blueprint.py"),
        "--persona-file", str(persona_file),
        "--output", str(out_blueprint),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def run_agent(blueprint_path: Path, out_trajectory: Path, run_id: str) -> bool:
    """调用 run_agent_simulation.py，使用 --tools-path 启动轻量 MCP，输出轨迹到 out_trajectory。"""
    out_trajectory.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(AGENT_DEMO / "run_agent_simulation.py"),
        "--blueprint", str(blueprint_path),
        "--tools-path", str(TOOLS_PATH),
        "--output", str(out_trajectory),
        "--run-id", run_id,
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def run_eval(trajectory_path: Path, out_eval: Path) -> bool:
    """调用 run_trajectory_eval.py，输出评估到 out_eval。"""
    out_eval.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(EVAL_DEMO / "run_trajectory_eval.py"),
        "--trajectory", str(trajectory_path),
        "--output", str(out_eval),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pipeline1: 20 人物 → 20 蓝图 → 20 轨迹 → 评估")
    parser.add_argument("--num", type=int, default=20, help="抽取人物数（默认 20）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，不传则随机")
    args = parser.parse_args()

    if not PERSONA_PATH.exists():
        print(f"ERROR: persona 文件不存在: {PERSONA_PATH}", file=sys.stderr)
        return 2
    if not TOOLS_PATH.exists():
        print(f"ERROR: tools.jsonl 不存在: {TOOLS_PATH}", file=sys.stderr)
        return 2

    personas = load_personas(PERSONA_PATH)
    if len(personas) < args.num:
        print(f"WARN: persona 仅 {len(personas)} 条，将全部使用", file=sys.stderr)
        sampled = personas
    else:
        if args.seed is not None:
            random.seed(args.seed)
        sampled = random.sample(personas, args.num)

    OUT_BLUEPRINTS.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)

    ok_blueprints = 0
    ok_trajectories = 0
    ok_evals = 0

    for i, persona_line in enumerate(sampled):
        run_id = f"pipeline1_{i}"
        print("=" * 60)
        print(f"[{i+1}/{len(sampled)}] persona_id ~ {json.loads(persona_line).get('id', '')[:8]}...")
        print("=" * 60)

        blueprint_path = OUT_BLUEPRINTS / f"blueprint_{i}.json"
        if run_blueprint(persona_line, blueprint_path, SCRATCH):
            ok_blueprints += 1
        else:
            print(f"  蓝图生成失败，跳过本条")
            continue

        traj_dir = OUT_TRAJECTORIES / str(i)
        traj_path = traj_dir / "out_trajectory.json"
        if not run_agent(blueprint_path, traj_path, run_id):
            print(f"  轨迹采集失败，跳过评估")
            continue
        ok_trajectories += 1

        # 将 messages 转为 turns，供 trajectory_eval 读取
        traj_data = json.loads(traj_path.read_text(encoding="utf-8"))
        messages = traj_data.get("messages", [])
        turns = messages_to_turns(messages)
        traj_data["turns"] = turns
        traj_for_eval_path = traj_dir / "out_trajectory_for_eval.json"
        traj_for_eval_path.write_text(json.dumps(traj_data, ensure_ascii=False, indent=2), encoding="utf-8")

        eval_path = OUT_EVALS / str(i) / "out_trajectory_eval.json"
        if run_eval(traj_for_eval_path, eval_path):
            ok_evals += 1

    print("=" * 60)
    print("pipeline1 完成")
    print(f"  蓝图: {ok_blueprints}/{len(sampled)}")
    print(f"  轨迹: {ok_trajectories}/{len(sampled)}")
    print(f"  评估: {ok_evals}/{len(sampled)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

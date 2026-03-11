#!/usr/bin/env python3
"""
pipeline1：从 persona_5K.jsonl 随机抽 N 个人物，生成蓝图、采集轨迹并做评估。

特性：
- MCP Server 在一开始启动，整个合成过程复用，合成结束后关闭。
- 轨迹文件中保存 tools.jsonl 的完整内容（tools_jsonl 字段）。
- 蓝图生成时，如果任务不涉及状态变更（如付款、订票），则 initial_state 和 expected_final_state 均为 {}。

依赖：src/astra（用于 MCP 启动）、自身目录的 scripts/、prompts/、data/。
- prompts/：按 4 个 agent 组织的提示词（planner/user/eval/tool）
- SKILL.md：技能定义
- tools.jsonl：工具定义
- data/persona_5K.jsonl：人物数据
需已安装 uv。
请在项目根目录执行：uv run python exps/data-synthesis-workflow/pipeline1/run.py [--num 20] [--seed 42]

输出产物：
- artifacts/{i}/blueprint.json：第 i 个蓝图
- artifacts/{i}/trajectory.json：第 i 条轨迹
- artifacts/{i}/evaluation.json：第 i 个评估结果
"""

from __future__ import annotations

import argparse
import atexit
import json
import random
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

# 路径：pipeline1/run.py -> exps -> 项目根
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# 本地脚本和资源
SCRIPTS_DIR = SCRIPT_DIR / "scripts"
PERSONA_PATH = SCRIPT_DIR / "data" / "persona_5K.jsonl"
TOOLS_PATH = SCRIPT_DIR / "tools.jsonl"

# MCP SSE 端点（本地轻量 MCP）
MCP_SSE_URL = "http://localhost:8000/sse"

ARTIFACTS_DIR = SCRIPT_DIR / "artifacts"

# 全局 MCP 进程句柄
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
def start_light_mcp_subprocess(tools_path: Path):
    """
    通过 astra run_light_mcp 子进程启动 MCP（SSE），就绪后 yield，退出时终止子进程。
    供 pipeline1 在一开始启动，整个合成过程复用。
    """
    global _light_mcp_proc
    tools_abs = tools_path.resolve() if not tools_path.is_absolute() else tools_path
    if not tools_abs.exists():
        raise FileNotFoundError(f"tools_path 不存在: {tools_abs}")

    # prompt_path 需要传递给 MCP 用于生成工具回复
    prompt_path = SCRIPT_DIR / "prompts" / "tool" / "tool_response_generator.md"
    prompt_abs = prompt_path.resolve() if not prompt_path.is_absolute() else prompt_path

    cmd = [
        "uv", "run", "-m", "astra.scripts.run_light_mcp",
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
    atexit.register(lambda: _light_mcp_proc and _light_mcp_proc.poll() is None and _light_mcp_proc.terminate())

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


def load_tools_jsonl(path: Path) -> list[dict]:
    """加载 tools.jsonl 内容为字典列表。"""
    tools = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    tools.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return tools


def run_blueprint(persona_line: str, out_blueprint: Path) -> bool:
    """直接传递 persona 字符串，调用 run_blueprint.py，输出到 out_blueprint。"""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_blueprint.py"),
        "--persona", persona_line.strip(),
        "--output", str(out_blueprint),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if r.returncode != 0:
        return False

    # 蓝图生成后，检查 initial_state：若所有值均为空（[]、{}、None），则设为 {}
    # 同时设置 expected_final_state 为 {}（无状态任务）
    try:
        blueprint_data = json.loads(out_blueprint.read_text(encoding="utf-8"))
        initial_state = blueprint_data.get("initial_state")
        if isinstance(initial_state, dict):
            all_empty = all((v == [] or v == {} or v is None) for v in initial_state.values())
            if all_empty:
                # 无状态任务：initial_state 和 expected_final_state 都设为 {}
                blueprint_data["initial_state"] = {}
                blueprint_data["expected_final_state"] = {}
                out_blueprint.write_text(json.dumps(blueprint_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  警告：处理蓝图状态时出错: {e}")
    return True


def run_agent(blueprint_path: Path, out_trajectory: Path, run_id: str, mcp_url: str) -> bool:
    """调用 run_simulation.py，传入 --mcp-url 复用已有 MCP，输出轨迹到 out_trajectory。"""
    out_trajectory.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_simulation.py"),
        "--blueprint", str(blueprint_path),
        "--mcp-url", mcp_url,
        "--output", str(out_trajectory),
        "--run-id", run_id,
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def run_eval(trajectory_path: Path, out_eval: Path) -> bool:
    """调用 run_evaluation.py，输出评估到 out_eval。"""
    out_eval.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_evaluation.py"),
        "--trajectory", str(trajectory_path),
        "--output", str(out_eval),
    ]
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="pipeline1: N 人物 → 蓝图 → 轨迹 → 评估（复用单个 MCP 实例）")
    parser.add_argument("--num", type=int, default=20, help="抽取人物数（默认 20）")
    parser.add_argument("--seed", type=int, default=None, help="随机种子，不传则随机")
    args = parser.parse_args()

    if not PERSONA_PATH.exists():
        print(f"ERROR: persona 文件不存在: {PERSONA_PATH}", file=sys.stderr)
        return 2
    if not TOOLS_PATH.exists():
        print(f"ERROR: tools.jsonl 不存在: {TOOLS_PATH}", file=sys.stderr)
        return 2

    # 预加载 tools.jsonl 内容（可选，供调试或日志用）
    tools_jsonl_content = load_tools_jsonl(TOOLS_PATH)
    print(f"已加载 {len(tools_jsonl_content)} 个工具定义")

    personas = load_personas(PERSONA_PATH)
    if len(personas) < args.num:
        print(f"WARN: persona 仅 {len(personas)} 条，将全部使用", file=sys.stderr)
        sampled = personas
    else:
        if args.seed is not None:
            random.seed(args.seed)
        sampled = random.sample(personas, args.num)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    ok_blueprints = 0
    ok_trajectories = 0
    ok_evals = 0

    # 在一开始启动 MCP，整个合成过程复用
    print("\n" + "=" * 60)
    print("启动 MCP Server（将被所有轨迹复用）")
    print("=" * 60)
    try:
        with start_light_mcp_subprocess(TOOLS_PATH):
            print("\nMCP Server 已就绪，开始合成...")

            for i, persona_line in enumerate(sampled):
                run_id = f"pipeline1_{i}"
                print("\n" + "=" * 60)
                print(f"[{i+1}/{len(sampled)}] persona_id ~ {json.loads(persona_line).get('id', '')[:8]}...")
                print("=" * 60)

                # 每个实验的产物放在 artifacts/{i}/ 目录下
                run_dir = ARTIFACTS_DIR / str(i)
                run_dir.mkdir(parents=True, exist_ok=True)

                blueprint_path = run_dir / "blueprint.json"
                if run_blueprint(persona_line, blueprint_path):
                    ok_blueprints += 1
                else:
                    print(f"  蓝图生成失败，跳过本条")
                    continue

                traj_path = run_dir / "trajectory.json"
                # 传入 MCP URL 复用已有实例
                if not run_agent(blueprint_path, traj_path, run_id, MCP_SSE_URL):
                    print(f"  轨迹采集失败，跳过评估")
                    continue
                ok_trajectories += 1

                eval_path = run_dir / "evaluation.json"
                if run_eval(traj_path, eval_path):
                    ok_evals += 1

            print("\n" + "=" * 60)
            print("所有轨迹合成完成，关闭 MCP Server")
            print("=" * 60)
    except Exception as e:
        print(f"ERROR: MCP 启动或运行失败: {e}", file=sys.stderr)
        return 1

    print("\n" + "=" * 60)
    print("pipeline1 完成")
    print(f"  蓝图: {ok_blueprints}/{len(sampled)}")
    print(f"  轨迹: {ok_trajectories}/{len(sampled)}")
    print(f"  评估: {ok_evals}/{len(sampled)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
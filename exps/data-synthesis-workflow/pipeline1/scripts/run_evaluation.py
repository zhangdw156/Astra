"""
轨迹质量评估 Demo：调用大模型，对单条 run 轨迹做质量 / 幻觉打分。

仅使用大模型评估，不做程序化校验。输入为原始轨迹 JSON（含 messages 数组的 flat 格式）。

依赖：
- 项目根 .env：OPENAI_API_KEY、OPENAI_MODEL，OPENAI_BASE_URL（可选）
- pip install openai python-dotenv

运行（在项目根目录）：
  python exps/data-synthesis-workflow/pipeline1/scripts/run_evaluation.py \
    --trajectory exps/data-synthesis-workflow/pipeline1/artifacts/0/trajectory.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import os

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
from astra.utils import config as astra_config

PROMPT_PATH = SCRIPT_DIR.parent / "prompts" / "eval_agent.md"
DEFAULT_TRAJECTORY_PATH = SCRIPT_DIR.parent / "artifacts" / "0" / "trajectory.json"


def build_default_eval_output_path(run_id: str) -> Path:
    """为每条轨迹构造评估结果路径（输出到 artifacts/{i}/evaluation.json）。"""
    idx = run_id.replace("pipeline1_", "")
    run_dir = SCRIPT_DIR.parent / "artifacts" / idx
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / "evaluation.json"


def load_env_and_client() -> tuple[OpenAI, str]:
    """从项目根 .env 加载 Eval Agent 配置并创建 OpenAI 客户端。"""
    api_key = astra_config.get_eval_agent_api_key()
    model = astra_config.get_eval_agent_model()
    base_url = astra_config.get_eval_agent_base_url()
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def load_trajectory(path: Path) -> dict:
    """读取单条轨迹 JSON。要求为原始轨迹，含 messages 数组（flat 格式：role/content/reasoning_content/function_call）。"""
    if not path.exists():
        raise SystemExit(f"轨迹文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "messages" not in data or not isinstance(data["messages"], list):
        raise SystemExit("轨迹 JSON 缺少 messages 字段或格式不正确（请使用原始轨迹，勿用 turns 转换格式）")
    return data


def build_prompt(trajectory: dict) -> str:
    """从模板与轨迹 JSON 构造最终提示词。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    traj_json = json.dumps(trajectory, ensure_ascii=False, indent=2)
    prompt_text = prompt_text.replace("{TRAJECTORY_JSON}", traj_json)
    return prompt_text


def extract_json_from_response(text: str) -> dict:
    """
    从模型回复中提取 JSON。

    规则：
    1. 优先解析 ```json ... ``` / ``` ... ``` 代码块中的内容；
    2. 否则截取第一个 '{' 到最后一个 '}' 之间的内容再解析；
    3. 最后才尝试整体解析。
    """
    text = text.strip()
    # 1) 尝试 ```json ... ``` 或 ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1).strip())

    # 2) 截取第一个 '{' 到最后一个 '}' 之间
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        core = text[start : end + 1]
        return json.loads(core)

    # 3) 回退到整体解析（理论上不应触发，作为兜底）
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="使用大模型对单条轨迹做质量 / 幻觉评估。"
    )
    parser.add_argument(
        "--trajectory",
        type=Path,
        default=DEFAULT_TRAJECTORY_PATH,
        help=f"轨迹 JSON 路径（默认: {DEFAULT_TRAJECTORY_PATH}）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="评估结果输出路径（默认: artifacts/{i}/evaluation.json）",
    )
    args = parser.parse_args()

    client, model = load_env_and_client()

    traj_path = args.trajectory
    if not traj_path.is_absolute():
        # 相对路径相对于 workflow 根或脚本目录均可，这里用 PROJECT_ROOT 兼容示例用法
        traj_path = PROJECT_ROOT / traj_path

    trajectory = load_trajectory(traj_path)
    prompt = build_prompt(trajectory)

    print("Calling model:", model)
    print("Prompt length:", len(prompt), "chars")
    print("-" * 60)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw = resp.choices[0].message.content or ""

    try:
        eval_result = extract_json_from_response(raw)
    except json.JSONDecodeError as e:
        print("Model output (raw):")
        print(raw)
        raise SystemExit(f"Failed to parse JSON from model output: {e}") from e

    eval_result["run_id"] = trajectory.get("run_id", "")

    print("Evaluation result:")
    print(json.dumps(eval_result, ensure_ascii=False, indent=2))
    print("-" * 60)

    run_id = trajectory.get("run_id", "").strip()
    out_path = args.output or (
        build_default_eval_output_path(run_id) if run_id else (SCRIPT_DIR / "out_trajectory_eval.json")
    )
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(eval_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Written to:", out_path)


if __name__ == "__main__":
    main()


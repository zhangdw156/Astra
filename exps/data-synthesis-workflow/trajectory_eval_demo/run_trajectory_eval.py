"""
轨迹质量评估 Demo：调用大模型，对 agent_demo/out_trajectory.json 这样的多轮轨迹做质量 / 幻觉打分。

支持程序化验证：若轨迹含 expected_output、expected_final_state、final_state_snapshot，
先做基于输出与基于状态的简单检查，结果作为上下文供 LLM 参考。

支持两种 turns 格式：turn-based（含 user_message、assistant_message、tool_calls）
与 flat（role/content）。

依赖：
- 项目根 .env：OPENAI_API_KEY、OPENAI_MODEL，OPENAI_BASE_URL（可选）
- pip install openai python-dotenv

运行（在项目根目录）：
  python exps/data-synthesis-workflow/trajectory_eval_demo/run_trajectory_eval.py \
    --trajectory exps/data-synthesis-workflow/agent_demo/out_trajectory.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent

PROMPT_PATH = WORKFLOW_DIR / "prompts" / "trajectory_evaluator.md"
DEFAULT_TRAJECTORY_PATH = WORKFLOW_DIR / "agent_demo" / "out_trajectory.json"


def load_env_and_client() -> tuple[OpenAI, str]:
    """从项目根 .env 加载并创建 OpenAI 客户端。"""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise SystemExit(
            "请在项目根目录 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL；可选 OPENAI_BASE_URL。"
        )
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def load_trajectory(path: Path) -> dict:
    """读取单条轨迹 JSON。"""
    if not path.exists():
        raise SystemExit(f"轨迹文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "turns" not in data or not isinstance(data["turns"], list):
        raise SystemExit("轨迹 JSON 缺少 turns 字段或格式不正确")
    return data


def compute_programmatic_validation(trajectory: dict) -> dict:
    """
    程序化验证：基于输出与状态的简单检查。
    返回 {"task_completion_score": float, "output_check": str, "state_check": str}
    """
    result = {
        "task_completion_score": 0.0,
        "output_check": "skipped",
        "state_check": "skipped",
    }

    turns = trajectory.get("turns", [])
    expected_output = trajectory.get("expected_output")
    expected_final_state = trajectory.get("expected_final_state")
    final_state_snapshot = trajectory.get("final_state_snapshot")

    # 获取最后一轮助手回复
    last_assistant_msg = ""
    if turns:
        last = turns[-1]
        if isinstance(last, dict):
            if "assistant_message" in last:
                last_assistant_msg = last.get("assistant_message", "") or ""
            elif last.get("role") == "assistant":
                last_assistant_msg = last.get("content", "") or ""

    # 基于输出的验证
    if expected_output:
        if last_assistant_msg and "[Error]" not in last_assistant_msg:
            result["output_check"] = "pass (assistant replied; compare with expected_output manually)"
            result["task_completion_score"] = 0.5  # 占位，LLM 可细化
        else:
            result["output_check"] = "fail (no valid final reply)"
    else:
        result["output_check"] = "no expected_output in trajectory"

    # 基于状态的验证
    if expected_final_state and final_state_snapshot:
        if isinstance(final_state_snapshot, dict) and len(final_state_snapshot) > 0:
            result["state_check"] = f"pass (snapshot has {list(final_state_snapshot.keys())})"
            result["task_completion_score"] = max(result["task_completion_score"], 0.5)
        else:
            result["state_check"] = "fail (empty snapshot)"
    elif final_state_snapshot is None:
        result["state_check"] = "skipped (no final_state_snapshot)"

    return result


def build_prompt(trajectory: dict, programmatic: dict | None = None) -> str:
    """从模板与轨迹 JSON 构造最终提示词。若提供 programmatic 验证结果，注入为上下文。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    traj_json = json.dumps(trajectory, ensure_ascii=False, indent=2)
    prompt_text = prompt_text.replace("{TRAJECTORY_JSON}", traj_json)
    if programmatic:
        prog_json = json.dumps(programmatic, ensure_ascii=False)
        prompt_text += f"\n\n## Programmatic Validation (for reference)\n{prog_json}\n"
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
        help="评估结果输出路径（默认: trajectory_eval_demo/out_trajectory_eval.json）",
    )
    args = parser.parse_args()

    client, model = load_env_and_client()

    traj_path = args.trajectory
    if not traj_path.is_absolute():
        # 相对路径相对于 workflow 根或脚本目录均可，这里用 PROJECT_ROOT 兼容示例用法
        traj_path = PROJECT_ROOT / traj_path

    trajectory = load_trajectory(traj_path)
    programmatic = compute_programmatic_validation(trajectory)
    print("Programmatic validation:", programmatic)
    prompt = build_prompt(trajectory, programmatic)

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

    # 合并程序化验证结果
    if "task_completion_score" not in eval_result:
        eval_result["task_completion_score"] = programmatic.get("task_completion_score", 0.0)
    eval_result["programmatic_validation"] = programmatic

    print("Evaluation result:")
    print(json.dumps(eval_result, ensure_ascii=False, indent=2))
    print("-" * 60)

    out_path = args.output or (SCRIPT_DIR / "out_trajectory_eval.json")
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path
    out_path.write_text(json.dumps(eval_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Written to:", out_path)


if __name__ == "__main__":
    main()


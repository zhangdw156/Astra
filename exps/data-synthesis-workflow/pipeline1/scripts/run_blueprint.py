"""
使用 task_blueprint_generator 提示词 + SKILL.md / tools.jsonl / persona 调用大模型生成任务蓝图。

输出：task_id、goals、possible_tool_calls（[[tools],[tools],...]）、initial_state、expected_final_state、
user_agent_config、end_condition。不生成 system_message、queries、expected_output、max_turns。

依赖项目根目录 .env 中的 OPENAI_API_KEY、OPENAI_MODEL，可选 OPENAI_BASE_URL。
运行方式（在项目根或本目录）：python exps/data-synthesis-workflow/pipeline1/scripts/run_blueprint.py
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from astra.utils import config as astra_config

# 脚本所在目录
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = astra_config.get_project_root()

SKILL_NAME = "2896_prediction-trader"

# pipeline1 本地资源（基于 skill name 定位资源目录）
SKILL_DIR = SCRIPT_DIR.parent / SKILL_NAME
PROMPT_PATH = SCRIPT_DIR.parent / "prompts" / "planner_agent.md"
SKILL_PATH = SKILL_DIR / "SKILL.md"
TOOLS_PATH = SKILL_DIR / "tools.jsonl"
DEFAULT_PERSONA_PATH = SCRIPT_DIR.parent / "data" / "persona_5K.jsonl"


def get_persona_path(persona_file: Path | None) -> Path:
    """若传入 persona_file 则使用，否则用默认 PERSONA_PATH；支持环境变量 OVERRIDE_PERSONA_PATH。"""
    if os.environ.get("OVERRIDE_PERSONA_PATH"):
        return Path(os.environ["OVERRIDE_PERSONA_PATH"])
    if persona_file is not None:
        return persona_file
    return DEFAULT_PERSONA_PATH


def load_env_and_client() -> tuple[OpenAI, str]:
    """从项目根 .env 加载 Planner Agent 配置并创建 OpenAI 客户端。"""
    api_key = astra_config.get_planner_agent_api_key()
    model = astra_config.get_planner_agent_model()
    base_url = astra_config.get_planner_agent_base_url()
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def read_prompt_and_inputs(persona_path: Path | None = None, persona_line: str | None = None) -> tuple[str, str]:
    """读取提示词模板并替换占位符；返回 (填充后的提示词, persona 那一行)。优先使用 persona_line，否则从 persona_path 读取。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    skill_content = SKILL_PATH.read_text(encoding="utf-8")
    tools_content = TOOLS_PATH.read_text(encoding="utf-8")

    # 优先使用传入的 persona_line，否则从文件读取
    if persona_line is None:
        path = get_persona_path(persona_path)
        persona_line = next(path.open(encoding="utf-8")).strip()

    prompt_text = prompt_text.replace("{SKILL_MD_CONTENT}", skill_content)
    prompt_text = prompt_text.replace("{TOOLS_JSONL_CONTENT}", tools_content)
    prompt_text = prompt_text.replace("{PERSONA_CONTENT}", persona_line)
    return prompt_text, persona_line


def extract_json_from_response(text: str) -> dict:
    """从模型回复中提取 JSON（允许被 markdown 代码块包裹或前后有说明文字）。"""
    text = text.strip()
    # 1) 尝试 ```json ... ``` 或 ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1).strip())
    # 2) 截取第一个 { 到最后一个 } 再解析（应对模型输出前有说明文字）
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    return json.loads(text)


REQUIRED_FIELDS = [
    "task_id",
    "goals",
    "possible_tool_calls",
    "initial_state",
    "user_agent_config",
    "end_condition",
]

USER_AGENT_CONFIG_KEYS = ("role", "personality", "knowledge_boundary")


def get_tool_names_from_jsonl(tools_path: Path) -> set[str]:
    """从 tools.jsonl 解析出所有工具名，用于校验 possible_tool_calls。"""
    names: set[str] = set()
    if not tools_path.exists():
        return names
    for line in tools_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "name" in obj:
                names.add(str(obj["name"]))
        except json.JSONDecodeError:
            continue
    return names


def validate_blueprint(data: dict, allowed_tool_names: set[str] | None = None) -> list[str]:
    """校验蓝图格式，返回错误列表；空列表表示通过。"""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")
    # initial_state / expected_final_state: 允许为对象或 null；expected_final_state 可选
    for key in ("initial_state", "expected_final_state"):
        if key in data and data[key] is not None and not isinstance(data[key], dict):
            errors.append(f"{key} 必须为 JSON 对象或 null")
    if "possible_tool_calls" in data:
        ptc = data["possible_tool_calls"]
        goals = data.get("goals", [])
        if not isinstance(ptc, list):
            errors.append("possible_tool_calls 必须为数组")
        elif not all(isinstance(inner, list) for inner in ptc):
            errors.append("possible_tool_calls 必须为嵌套数组 [[tools],[tools],...]")
        elif len(ptc) != len(goals):
            errors.append(f"possible_tool_calls 长度 ({len(ptc)}) 必须与 goals 长度 ({len(goals)}) 一致")
        elif allowed_tool_names is not None:
            for i, inner in enumerate(ptc):
                for name in inner:
                    if name not in allowed_tool_names:
                        errors.append(f"possible_tool_calls[{i}] 中含非法工具名: {name!r}，应在 tools.jsonl 的 name 列表中")
    if "goals" in data:
        g = data["goals"]
        if not isinstance(g, list):
            errors.append("goals 必须为数组")
        elif len(g) == 0:
            errors.append("goals 不能为空，应包含至少一个目标")
        else:
            for i, item in enumerate(g):
                if not isinstance(item, str) or not item.strip():
                    errors.append(f"goals[{i}] 必须为非空字符串")
    if "user_agent_config" in data:
        uac = data["user_agent_config"]
        if not isinstance(uac, dict):
            errors.append("user_agent_config 必须为对象")
        else:
            for k in USER_AGENT_CONFIG_KEYS:
                if k not in uac:
                    errors.append(f"user_agent_config 缺少字段: {k}")
    return errors


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="使用 task_blueprint_generator 提示词生成任务蓝图")
    parser.add_argument("--persona-file", type=Path, default=None, help="单行 persona JSONL 文件路径，未指定则用默认 persona_5K.jsonl 首行")
    parser.add_argument("--persona", type=str, default=None, help="直接传入 persona JSON 字符串（完整的一行）")
    parser.add_argument("--output", "-o", type=Path, default=None, help="蓝图 JSON 输出路径，未指定则写入 artifacts/{i}/blueprint.json")
    args = parser.parse_args()

    client, model = load_env_and_client()
    persona_path = args.persona_file.resolve() if args.persona_file else None
    prompt, persona_line = read_prompt_and_inputs(persona_path, persona_line=args.persona)

    print("Calling model:", model)
    print("Prompt length:", len(prompt), "chars")
    print("-" * 60)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content or ""

    try:
        data = extract_json_from_response(raw)
    except json.JSONDecodeError as e:
        print("Model output (raw):")
        print(raw)
        raise SystemExit(f"Failed to parse JSON: {e}") from e

    # 程序注入字段不应由模型输出，若存在则移除避免覆盖
    for key in ("blueprint_id", "skill_name", "persona_id", "created_at"):
        data.pop(key, None)

    allowed_tool_names = get_tool_names_from_jsonl(TOOLS_PATH)
    validation_errors = validate_blueprint(data, allowed_tool_names=allowed_tool_names)
    if validation_errors:
        print("蓝图格式校验失败:")
        for e in validation_errors:
            print("  -", e)
        print("当前解析出的蓝图（前 2000 字符）:")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])
        raise SystemExit("请检查 prompt 与模型输出是否符合新 schema")

    # 程序注入字段
    persona_obj = json.loads(persona_line)
    data["blueprint_id"] = str(uuid.uuid4())
    data["skill_name"] = SKILL_NAME
    data["persona_id"] = persona_obj.get("id", "")
    data["created_at"] = datetime.now(timezone.utc).isoformat()

    # 若 initial_state 仅包含空值（如空数组/对象），则视为无状态环境，可省略 expected_final_state
    initial_state = data.get("initial_state")
    if isinstance(initial_state, dict):
        if all(
            (v == [] or v == {} or v is None)
            for v in initial_state.values()
        ):
            data.pop("expected_final_state", None)

    print("Blueprint (with program-injected fields):")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("-" * 60)

    out_path = args.output if args.output else (SCRIPT_DIR.parent / "artifacts" / "0" / "blueprint.json")
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Written to:", out_path)


if __name__ == "__main__":
    main()

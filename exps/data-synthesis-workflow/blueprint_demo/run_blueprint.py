"""
使用 task_blueprint_generator 提示词 + SKILL.md / tools.jsonl / persona 调用大模型生成任务蓝图。

依赖项目根目录 .env 中的 OPENAI_API_KEY、OPENAI_MODEL，可选 OPENAI_BASE_URL。
运行方式（在项目根或本目录）：python exps/data-synthesis-workflow/blueprint_demo/run_blueprint.py
"""

import json
import os
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 脚本所在目录与 workflow 目录、项目根
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

PROMPT_PATH = WORKFLOW_DIR / "prompts" / "task_blueprint_generator.md"
SKILL_PATH = WORKFLOW_DIR / "2896_prediction-trader" / "SKILL.md"
TOOLS_PATH = WORKFLOW_DIR / "prediction-trader" / "tools.jsonl"
PERSONA_PATH = PROJECT_ROOT / "persona" / "persona_5K.jsonl"

SKILL_NAME = "prediction-trader"


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


def read_prompt_and_inputs() -> tuple[str, str]:
    """读取提示词模板并替换占位符；返回 (填充后的提示词, persona 那一行)。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")
    skill_content = SKILL_PATH.read_text(encoding="utf-8")
    tools_content = TOOLS_PATH.read_text(encoding="utf-8")
    persona_line = next(PERSONA_PATH.open(encoding="utf-8")).strip()

    prompt_text = prompt_text.replace("{SKILL_MD_CONTENT}", skill_content)
    prompt_text = prompt_text.replace("{TOOLS_JSONL_CONTENT}", tools_content)
    prompt_text = prompt_text.replace("{PERSONA_CONTENT}", persona_line)
    return prompt_text, persona_line


def extract_json_from_response(text: str) -> dict:
    """从模型回复中提取 JSON（允许被 markdown 代码块包裹）。"""
    text = text.strip()
    # 尝试 ```json ... ``` 或 ``` ... ```
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        return json.loads(m.group(1).strip())
    return json.loads(text)


def main() -> None:
    client, model = load_env_and_client()
    prompt, persona_line = read_prompt_and_inputs()

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

    # 程序注入字段
    persona_obj = json.loads(persona_line)
    data["blueprint_id"] = str(uuid.uuid4())
    data["skill_name"] = SKILL_NAME
    data["persona_id"] = persona_obj.get("id", "")

    print("Blueprint (with program-injected fields):")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("-" * 60)

    out_path = SCRIPT_DIR / "out_blueprint.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Written to:", out_path)


if __name__ == "__main__":
    main()

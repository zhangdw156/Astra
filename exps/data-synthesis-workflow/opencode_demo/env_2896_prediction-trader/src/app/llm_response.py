"""
工具回复与状态更新生成模块（位于 src/app 中的核心逻辑）。

职责：
- 基于 tool_name / arguments / raw_result / 当前状态 等信息，
  调用大模型生成用户可见回复（Markdown）与新的完整状态 JSON。
- 使用 prompts/tool_response_generator.md 作为提示词模板。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


# 容器内 WORK_DIR=/work，/work 下有 .env、prompts/、app/
# 本地则从 env 目录推导 workflow 与项目根
_WORK_DIR = os.environ.get("WORK_DIR")
if _WORK_DIR:
    _WORK = Path(_WORK_DIR)
    PROMPT_PATH = _WORK / "prompts" / "tool_response_generator.md"
    _ENV_PATH = _WORK / ".env"
else:
    ENV_DIR = Path(__file__).resolve().parents[2]
    WORKFLOW_DIR = ENV_DIR.parent.parent
    PROMPT_PATH = WORKFLOW_DIR / "prompts" / "tool_response_generator.md"
    _ENV_PATH = WORKFLOW_DIR.parent.parent / ".env"


def _load_client() -> Tuple[OpenAI, str]:
    """从环境变量加载 OpenAI 客户端与模型名；优先从挂载的 .env 加载。"""
    load_dotenv(_ENV_PATH)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise RuntimeError(
            "缺少 OPENAI_API_KEY 或 OPENAI_MODEL 环境变量，无法生成工具回复。"
        )
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


def _build_prompt(
    tool_name: str,
    arguments: str,
    current_state: Optional[Dict[str, Any]] = None,
    conversation_context: str | None = None,
) -> str:
    """根据模板与上下文构造提示词。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")

    prompt_text = prompt_text.replace("{TOOL_NAME}", tool_name)
    prompt_text = prompt_text.replace("{TOOL_ARGUMENTS}", arguments or "{}")
    prompt_text = prompt_text.replace(
        "{CURRENT_STATE}",
        json.dumps(current_state or {}, ensure_ascii=False, indent=2),
    )
    prompt_text = prompt_text.replace(
        "{CONVERSATION_CONTEXT}", (conversation_context or "").strip() or "(empty)"
    )
    return prompt_text


def _parse_response(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析模型输出中的 <RESPONSE> 与 <STATE> 块。

    RESPONSE 应为工具返回的 JSON；解析后以紧凑 JSON 字符串返回，供 Assistant 解析。
    返回 (response_json_str, new_state_dict)。
    """
    # 提取 RESPONSE
    resp_match = re.search(
        r"<RESPONSE>\s*([\s\S]*?)\s*</RESPONSE>", text, flags=re.IGNORECASE
    )
    raw_response = (resp_match.group(1).strip() if resp_match else text.strip()) or ""

    # RESPONSE 应为 JSON：尝试解析并返回紧凑字符串；若非 JSON 则包装为 {"raw": "..."}
    response_str: str
    try:
        parsed = json.loads(raw_response)
        response_str = json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        # 尝试截取第一个 { ... } 作为 JSON
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start != -1 and end > start:
            try:
                parsed = json.loads(raw_response[start:end])
                response_str = json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                response_str = json.dumps({"raw": raw_response[:2000], "parse_error": True})
        else:
            response_str = json.dumps({"raw": raw_response[:2000], "parse_error": True})

    # 提取 STATE
    state_match = re.search(
        r"<STATE>\s*([\s\S]*?)\s*</STATE>", text, flags=re.IGNORECASE
    )
    state_obj: Dict[str, Any] = {}
    if state_match:
        raw_state = state_match.group(1).strip()
        try:
            parsed = json.loads(raw_state or "{}")
            if isinstance(parsed, dict):
                state_obj = parsed
        except json.JSONDecodeError:
            state_obj = {}

    return response_str, state_obj


def generate_tool_response(
    tool_name: str,
    arguments_json: str,
    session_state: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    调用大模型生成工具回复与新状态。

    参数：
    - tool_name: 工具名。
    - arguments_json: 工具参数（JSON 字符串，已按 Schema 序列化）。
    - session_state: 当前会话状态 JSON（KV 中存储的完整状态）。
    - conversation_context: 近期对话与工具调用摘要。

    返回：
    {
      "response": "<Markdown 文本>",
      "state": { ... 完整的新状态 JSON ... }
    }
    """
    client, model = _load_client()
    prompt = _build_prompt(
        tool_name=tool_name,
        arguments=arguments_json,
        current_state=session_state,
        conversation_context=conversation_context,
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    content = (resp.choices[0].message.content or "").strip()
    response_md, new_state = _parse_response(content)
    return {"response": response_md, "state": new_state}


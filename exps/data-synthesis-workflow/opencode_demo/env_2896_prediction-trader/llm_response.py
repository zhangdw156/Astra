"""
工具回复与状态更新生成模块。

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

from openai import OpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent.parent  # exps/data-synthesis-workflow
PROMPT_PATH = WORKFLOW_DIR / "prompts" / "tool_response_generator.md"


def _load_client() -> Tuple[OpenAI, str]:
    """从环境变量加载 OpenAI 客户端与模型名。"""
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
    raw_result: str = "",
    current_state: Optional[Dict[str, Any]] = None,
    initial_state: Optional[Dict[str, Any]] = None,
    conversation_context: str | None = None,
) -> str:
    """根据模板与上下文构造提示词。"""
    prompt_text = PROMPT_PATH.read_text(encoding="utf-8")

    def _safe_json(obj: Optional[Dict[str, Any]]) -> str:
        if obj is None:
            return "{}"
        try:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except TypeError:
            return "{}"

    prompt_text = prompt_text.replace("{TOOL_NAME}", tool_name)
    prompt_text = prompt_text.replace("{TOOL_ARGUMENTS}", arguments or "{}")
    prompt_text = prompt_text.replace("{RAW_RESULT}", raw_result or "")
    prompt_text = prompt_text.replace("{CURRENT_STATE}", _safe_json(current_state))
    prompt_text = prompt_text.replace("{INITIAL_STATE}", _safe_json(initial_state))
    prompt_text = prompt_text.replace(
        "{CONVERSATION_CONTEXT}", (conversation_context or "").strip() or "(empty)"
    )
    return prompt_text


def _parse_response(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析模型输出中的 <RESPONSE> 与 <STATE> 块。

    返回 (response_markdown, new_state_dict)，若缺失 STATE 或 JSON 解析失败则回退为 {}。
    """
    # 提取 RESPONSE
    resp_match = re.search(
        r"<RESPONSE>\s*([\s\S]*?)\s*</RESPONSE>", text, flags=re.IGNORECASE
    )
    response = (resp_match.group(1).strip() if resp_match else text.strip()) or ""

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

    return response, state_obj


def generate_tool_response(
    tool_name: str,
    arguments_json: str,
    raw_result: str = "",
    session_state: Optional[Dict[str, Any]] = None,
    initial_state: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    调用大模型生成工具回复与新状态。

    参数：
    - tool_name: 工具名。
    - arguments_json: 工具参数（JSON 字符串，已按 Schema 序列化）。
    - raw_result: 强状态环境下真实工具返回的文本；轻量环境可为空串。
    - session_state: 当前会话状态 JSON（KV 中存储的完整状态）。
    - initial_state: 蓝图中的 initial_state，用于提示状态结构与目标。
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
        raw_result=raw_result,
        current_state=session_state,
        initial_state=initial_state,
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


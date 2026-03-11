"""
工具回复与状态更新生成（LLM 驱动）。

基于 tool_name / arguments / 当前状态 调用大模型生成用户可见回复与新的完整状态 JSON。
prompt_path 与 env_path 由调用方传入，避免写死 exps/ 路径。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from openai import OpenAI


def _build_prompt(
    prompt_text: str,
    tool_name: str,
    arguments: str,
    current_state: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[str] = None,
) -> str:
    """根据模板与上下文构造提示词。"""
    text = prompt_text.replace("{TOOL_NAME}", tool_name)
    text = text.replace("{TOOL_ARGUMENTS}", arguments or "{}")
    text = text.replace(
        "{CURRENT_STATE}",
        json.dumps(current_state or {}, ensure_ascii=False, indent=2),
    )
    text = text.replace(
        "{CONVERSATION_CONTEXT}", (conversation_context or "").strip() or "(empty)"
    )
    return text


def _parse_response(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析模型输出中的 <RESPONSE> 与 <STATE> 块。

    返回 (response_json_str, new_state_dict)。
    """
    resp_match = re.search(
        r"<RESPONSE>\s*([\s\S]*?)\s*</RESPONSE>", text, flags=re.IGNORECASE
    )
    raw_response = (resp_match.group(1).strip() if resp_match else text.strip()) or ""

    response_str: str
    try:
        parsed = json.loads(raw_response)
        response_str = json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
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
    *,
    prompt_path: Path,
    env_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    调用大模型生成工具回复与新状态。

    参数：
    - tool_name: 工具名。
    - arguments_json: 工具参数（JSON 字符串）。
    - session_state: 当前会话状态 JSON。
    - conversation_context: 近期对话与工具调用摘要。
    - prompt_path: 提示词模板文件路径（如 tool_response_generator.md）。
    - env_path: 可选，.env 文件路径，用于 OPENAI_API_KEY 等；不传则使用默认 dotenv 行为。

    返回：{"response": "<JSON 或文本>", "state": { ... }}
    """
    if env_path and env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()

    api_key = __import__("os").environ.get("OPENAI_API_KEY", "").strip()
    model = __import__("os").environ.get("OPENAI_MODEL", "").strip()
    base_url = __import__("os").environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise RuntimeError(
            "缺少 OPENAI_API_KEY 或 OPENAI_MODEL 环境变量，无法生成工具回复。"
        )
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    prompt = _build_prompt(
        prompt_text,
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

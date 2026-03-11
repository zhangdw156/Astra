"""
轻量 MCP 服务：基于 tools.jsonl 注册通用 LLM 工具 handler。

状态存储在进程内 KV；参数归一化可由配置提供或从 inputSchema.required 推导。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from astra.data_synthesis.tool_response import generate_tool_response

# 进程内状态存储，key -> state dict
_STATE_STORE: Dict[str, Dict[str, Any]] = {}
_DEFAULT_STATE_KEY = "default"


def _get_state(key: str = _DEFAULT_STATE_KEY) -> Dict[str, Any]:
    """获取当前会话状态。"""
    return _STATE_STORE.get(key, {})


def _set_state(state: Dict[str, Any], key: str = _DEFAULT_STATE_KEY) -> None:
    """写回当前会话状态。"""
    _STATE_STORE[key] = state or {}


def _infer_primary_param(schema: Dict[str, Any]) -> Optional[str]:
    """从 inputSchema.required 取第一个作为主参；若无则返回 None。"""
    schema = schema.get("inputSchema") if isinstance(schema.get("inputSchema"), dict) else None
    if not schema:
        return None
    required = schema.get("required")
    if isinstance(required, list) and len(required) > 0:
        return str(required[0])
    return None


def _normalize_handler_args(
    tool_name: str,
    kwargs: Dict[str, Any],
    primary_param: Optional[str],
) -> Dict[str, Any]:
    """
    将 MCP 客户端传来的 kwargs 归一化：若仅有 "kwargs" 且为字符串，则映射为主参。
    """
    if not kwargs or "kwargs" not in kwargs:
        return kwargs
    if not primary_param:
        return kwargs
    val = kwargs.get("kwargs")
    if isinstance(val, str) and val.strip():
        return {primary_param: val.strip(), **{k: v for k, v in kwargs.items() if k != "kwargs"}}
    return kwargs


def create_mcp_tools_light(
    mcp: Any,
    tools: List[Dict[str, Any]],
    *,
    prompt_path: Path,
    env_path: Optional[Path] = None,
    param_normalizer: Optional[Dict[str, str]] = None,
    state_key: str = _DEFAULT_STATE_KEY,
) -> None:
    """
    基于 tools 列表向 FastMCP 实例注册通用 LLM 工具 handler。

    参数：
    - mcp: FastMCP 实例。
    - tools: load_tools_from_jsonl 返回的 schema 列表。
    - prompt_path: 工具回复生成所用的提示词模板路径。
    - env_path: 可选，.env 路径。
    - param_normalizer: 可选，tool_name -> 主参 key；未提供时从 inputSchema.required[0] 推导。
    - state_key: 会话状态在进程内存储的 key。
    """
    from fastmcp import FastMCP

    if not isinstance(mcp, FastMCP):
        raise TypeError("mcp 须为 FastMCP 实例")

    param_normalizer = param_normalizer or {}

    for schema in tools:
        name = schema.get("name")
        if not name:
            continue
        primary = param_normalizer.get(name) or _infer_primary_param(schema)

        def _handler(
            _name: str = name,
            _primary: Optional[str] = primary,
            **kwargs: Any,
        ) -> str:
            normalized = _normalize_handler_args(_name, dict(kwargs or {}), _primary)
            current_state = _get_state(state_key)
            args_json = json.dumps(normalized, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=_name,
                arguments_json=args_json,
                session_state=current_state,
                conversation_context=None,
                prompt_path=prompt_path,
                env_path=env_path,
            )
            new_state = out.get("state")
            if isinstance(new_state, dict):
                _set_state(new_state, state_key)
            response = (out.get("response") or "").strip()
            if not response:
                response = json.dumps({"status": "executed", "tool": _name})
            return response

        mcp.add_tool(
            _handler,
            name=name,
            description=schema.get("description", ""),
        )

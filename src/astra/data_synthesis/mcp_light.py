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


def _extract_params_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """从 inputSchema 中提取参数定义。"""
    input_schema = schema.get("inputSchema", {})
    if not isinstance(input_schema, dict):
        return {}
    return input_schema.get("properties", {})


def _make_tool_handler(
    tool_name: str,
    tool_description: str,
    primary_param: Optional[str],
    tool_params: Dict[str, Any],
    prompt_path: Path,
    env_path: Optional[Path],
    state_key: str,
) -> Any:
    """工厂函数：为每个工具创建正确签名的处理函数。"""
    from fastmcp.tools import tool

    param_names = list(tool_params.keys())

    if not param_names:
        # 无参数工具
        @tool(name=tool_name, description=tool_description)
        def _handler() -> str:
            current_state = _get_state(state_key)
            args_json = json.dumps({}, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
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
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response
        return _handler

    elif len(param_names) == 1:
        # 单参数工具
        p_name = param_names[0]
        p_info = tool_params[p_name]
        default = p_info.get("default")

        @tool(name=tool_name, description=tool_description)
        def _handler(arg: Optional[str] = default) -> str:
            kwargs = {p_name: arg} if arg is not None else {}
            normalized = _normalize_handler_args(tool_name, kwargs, primary_param)
            current_state = _get_state(state_key)
            args_json = json.dumps(normalized, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
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
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response
        return _handler

    else:
        # 多参数工具（取前两个）
        p1_name, p2_name = param_names[:2]
        p1_default = tool_params[p1_name].get("default")
        p2_default = tool_params[p2_name].get("default")

        @tool(name=tool_name, description=tool_description)
        def _handler(
            arg1: Optional[str] = p1_default,
            arg2: Optional[int] = p2_default,
        ) -> str:
            kwargs = {}
            if arg1 is not None:
                kwargs[p1_name] = arg1
            if arg2 is not None:
                kwargs[p2_name] = arg2
            normalized = _normalize_handler_args(tool_name, kwargs, primary_param)
            current_state = _get_state(state_key)
            args_json = json.dumps(normalized, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
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
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response
        return _handler


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
        description = schema.get("description", "")
        params = _extract_params_from_schema(schema)

        # 使用工厂函数创建正确签名的处理函数
        handler = _make_tool_handler(
            tool_name=name,
            tool_description=description,
            primary_param=primary,
            tool_params=params,
            prompt_path=prompt_path,
            env_path=env_path,
            state_key=state_key,
        )
        mcp.add_tool(handler)

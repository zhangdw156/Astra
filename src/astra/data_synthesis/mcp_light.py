"""
轻量 MCP 服务：基于 tools.jsonl 注册通用 LLM 工具 handler。

状态存储在进程内 KV；参数归一化可由配置提供或从 inputSchema.required 推导。
"""

from __future__ import annotations

import json
import inspect
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


def _extract_runtime_state_key(
    kwargs: Dict[str, Any],
    default_state_key: str,
) -> tuple[str, Dict[str, Any]]:
    """
    允许调用方通过保留参数 __state_key 指定本次调用的状态分区。
    返回 (state_key, clean_kwargs)。
    """
    if not isinstance(kwargs, dict):
        return default_state_key, {}
    runtime_key = kwargs.get("__state_key")
    clean_kwargs = {k: v for k, v in kwargs.items() if k != "__state_key"}
    if isinstance(runtime_key, str) and runtime_key.strip():
        return runtime_key.strip(), clean_kwargs
    return default_state_key, clean_kwargs


def _extract_params_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """从 inputSchema 中提取参数定义。"""
    input_schema = schema.get("inputSchema", {})
    if not isinstance(input_schema, dict):
        return {}
    return input_schema.get("properties", {})


def _schema_type_to_pytype(schema_type: Any) -> Any:
    """将 JSON Schema 基础类型映射到 Python 注解类型。"""
    if schema_type == "integer":
        return int
    if schema_type == "number":
        return float
    if schema_type == "boolean":
        return bool
    if schema_type == "array":
        return list
    if schema_type == "object":
        return dict
    return str


def _apply_explicit_signature(
    handler: Any,
    *,
    tool_params: Dict[str, Any],
    allow_kwargs_fallback: bool = True,
) -> None:
    """
    给 handler 注入显式签名，避免 FastMCP 因 **kwargs 拒绝注册。
    同时保留 __state_key（状态分区）与 kwargs（参数兜底）入口。
    """
    parameters: list[inspect.Parameter] = []
    annotations: Dict[str, Any] = {}

    for name, info in tool_params.items():
        if not isinstance(name, str):
            continue
        # 仅支持合法 Python 标识符；非法名称跳过（仍可走 kwargs 兜底）
        if not name.isidentifier() or name in ("kwargs", "__state_key"):
            continue
        schema_type = info.get("type", "string") if isinstance(info, dict) else "string"
        pytype = _schema_type_to_pytype(schema_type)
        default = None
        if isinstance(info, dict) and "default" in info:
            default = info.get("default")
        parameters.append(
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=pytype,
            )
        )
        annotations[name] = pytype

    if allow_kwargs_fallback and "kwargs" not in tool_params:
        parameters.append(
            inspect.Parameter(
                name="kwargs",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation=str,
            )
        )
        annotations["kwargs"] = str

    if "__state_key" not in tool_params:
        parameters.append(
            inspect.Parameter(
                name="__state_key",
                kind=inspect.Parameter.KEYWORD_ONLY,
                default="",
                annotation=str,
            )
        )
        annotations["__state_key"] = str

    handler.__signature__ = inspect.Signature(
        parameters=parameters,
        return_annotation=str,
    )
    handler.__annotations__ = {**annotations, "return": str}


def _make_tool_handler(
    tool_name: str,
    tool_description: str,
    primary_param: Optional[str],
    tool_params: Dict[str, Any],
    tool_schema: Dict[str, Any],
    available_tools: List[Dict[str, Any]],
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
        def _handler(**kwargs: Any) -> str:
            runtime_state_key, _ = _extract_runtime_state_key(kwargs, state_key)
            current_state = _get_state(runtime_state_key)
            args_json = json.dumps({}, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
                arguments_json=args_json,
                session_state=current_state,
                conversation_context=None,
                prompt_path=prompt_path,
                env_path=env_path,
                tool_schema=tool_schema,
                available_tools=available_tools,
            )
            new_state = out.get("state")
            if isinstance(new_state, dict):
                _set_state(new_state, runtime_state_key)
            response = (out.get("response") or "").strip()
            if not response:
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response
        _apply_explicit_signature(_handler, tool_params=tool_params)
        return _handler

    elif len(param_names) == 1:
        # 单参数工具
        p_name = param_names[0]
        p_info = tool_params[p_name]
        p_type = p_info.get("type", "string")
        default = p_info.get("default")

        @tool(name=tool_name, description=tool_description)
        def _handler(**kwargs: Any) -> str:
            runtime_state_key, runtime_kwargs = _extract_runtime_state_key(kwargs, state_key)
            normalized = _normalize_handler_args(tool_name, runtime_kwargs, primary_param)
            current_state = _get_state(runtime_state_key)
            args_json = json.dumps(normalized, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
                arguments_json=args_json,
                session_state=current_state,
                conversation_context=None,
                prompt_path=prompt_path,
                env_path=env_path,
                tool_schema=tool_schema,
                available_tools=available_tools,
            )
            new_state = out.get("state")
            if isinstance(new_state, dict):
                _set_state(new_state, runtime_state_key)
            response = (out.get("response") or "").strip()
            if not response:
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response

        _apply_explicit_signature(_handler, tool_params=tool_params)
        return _handler

    else:
        # 多参数工具（取前两个，使用 schema 中定义的参数名）
        p1_name = param_names[0]
        p2_name = param_names[1]
        p1_info = tool_params[p1_name]
        p2_info = tool_params[p2_name]
        p1_default = p1_info.get("default")
        p2_default = p2_info.get("default")

        @tool(name=tool_name, description=tool_description)
        def _handler(**kwargs: Any) -> str:
            runtime_state_key, runtime_kwargs = _extract_runtime_state_key(kwargs, state_key)
            normalized = _normalize_handler_args(tool_name, runtime_kwargs, primary_param)
            current_state = _get_state(runtime_state_key)
            args_json = json.dumps(normalized, ensure_ascii=False)
            out = generate_tool_response(
                tool_name=tool_name,
                arguments_json=args_json,
                session_state=current_state,
                conversation_context=None,
                prompt_path=prompt_path,
                env_path=env_path,
                tool_schema=tool_schema,
                available_tools=available_tools,
            )
            new_state = out.get("state")
            if isinstance(new_state, dict):
                _set_state(new_state, runtime_state_key)
            response = (out.get("response") or "").strip()
            if not response:
                response = json.dumps({"status": "executed", "tool": tool_name})
            return response

        _apply_explicit_signature(_handler, tool_params=tool_params)
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
            tool_schema=schema,
            available_tools=tools,
            prompt_path=prompt_path,
            env_path=env_path,
            state_key=state_key,
        )
        mcp.add_tool(handler)

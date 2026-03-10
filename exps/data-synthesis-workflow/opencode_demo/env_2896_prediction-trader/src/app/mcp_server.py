#!/usr/bin/env python3
"""
Prediction-trader 轻量 MCP 环境入口：基于 tools.jsonl 注册工具，使用 LLM 生成工具回复与 KV 状态。

容器内通过 WORK_DIR=/work 指定工作目录，/work 下包含 .env、app/、prompts/、tools.jsonl。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from fastmcp import FastMCP

from . import llm_response


_STATE_STORE: Dict[str, Dict[str, Any]] = {}
_DEFAULT_STATE_KEY = "default"


def _get_state(key: str = _DEFAULT_STATE_KEY) -> Dict[str, Any]:
    """获取当前会话状态（light 模式用）。"""
    return _STATE_STORE.get(key, {})


def _set_state(state: Dict[str, Any], key: str = _DEFAULT_STATE_KEY) -> None:
    """写回当前会话状态（light 模式用）。"""
    _STATE_STORE[key] = state or {}


def load_tools_from_jsonl(tools_jsonl: Path) -> List[Dict[str, Any]]:
    """解析 tools.jsonl（轻量环境）。"""
    tools: List[Dict[str, Any]] = []
    if not tools_jsonl.exists():
        return tools
    for line in tools_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "name" in obj:
                tools.append(obj)
        except json.JSONDecodeError:
            print(f"Invalid JSON in tools.jsonl line: {line[:120]}...")
    return tools


_TOOL_PRIMARY_PARAM: Dict[str, str] = {
    "polymarket_search": "query",
    "kalshi_search": "query",
    "compare_markets": "topic",
    "analyze_topic": "topic",
}


def _normalize_handler_args(tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """将 MCP 客户端传来的 kwargs 包装归一化为 tools.jsonl 定义的参数。"""
    if not kwargs or "kwargs" not in kwargs:
        return kwargs
    primary = _TOOL_PRIMARY_PARAM.get(tool_name)
    if not primary:
        return kwargs
    val = kwargs.get("kwargs")
    if isinstance(val, str) and val.strip():
        return {primary: val.strip(), **{k: v for k, v in kwargs.items() if k != "kwargs"}}
    return kwargs


def _make_json_only_handler(tool_name: str):
    """轻量模式 handler：完全依赖 LLM 生成回复 + 状态。"""

    def _handler(**kwargs):
        normalized = _normalize_handler_args(tool_name, dict(kwargs or {}))
        current_state = _get_state()
        args_json = json.dumps(normalized, ensure_ascii=False)
        out = llm_response.generate_tool_response(
            tool_name=tool_name,
            arguments_json=args_json,
            session_state=current_state,
            conversation_context=None,
        )
        new_state = out.get("state")
        if isinstance(new_state, dict):
            _set_state(new_state)
        response = (out.get("response") or "").strip()
        if not response:
            response = json.dumps({"status": "executed", "tool": tool_name})
        return response

    return _handler


def create_mcp_tools_light(mcp: FastMCP, tools: List[Dict[str, Any]]) -> None:
    """基于 tools.jsonl 注册通用 LLM 工具 handler。"""
    for schema in tools:
        name = schema.get("name")
        if not name:
            continue
        handler = _make_json_only_handler(name)
        mcp.add_tool(
            handler,
            name=name,
            description=schema.get("description", ""),
        )


def main():
    """主入口：容器内 WORK_DIR=/work，/work 下有 tools.jsonl、app/、prompts/、.env。"""
    work_dir = os.environ.get("WORK_DIR")
    if work_dir:
        work = Path(work_dir)
        tools_jsonl = work / "tools.jsonl"
        mcp_name = "prediction-trader"
    else:
        # 本地运行：从 env 目录定位
        env_dir = Path(__file__).resolve().parents[2]
        tools_jsonl = env_dir / "tools.jsonl"
        mcp_name = env_dir.name

    print(f"{mcp_name} MCP Server")
    print(f"tools.jsonl: {tools_jsonl}")
    print("-" * 40)

    mcp = FastMCP(mcp_name)
    jsonl_tools = load_tools_from_jsonl(tools_jsonl)
    print(f"Total tools loaded from JSONL: {len(jsonl_tools)}")
    print("-" * 40)
    create_mcp_tools_light(mcp, jsonl_tools)

    print("\nStarting MCP server...")
    if os.environ.get("MCP_TRANSPORT") in ("http", "sse"):
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()

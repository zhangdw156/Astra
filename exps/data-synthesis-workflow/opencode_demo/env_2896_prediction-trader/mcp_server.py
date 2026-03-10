#!/usr/bin/env python3
"""
MCP 服务入口：根据环境模式加载工具并注册为 MCP。

- strong 模式：扫描 tools/ 目录并注册 TOOL_SCHEMA + execute（真实 DB 工具）。
- light/json-only 模式：仅依赖 tools.jsonl，使用 LLM 生成工具回复与 KV 状态。

服务名使用当前目录名（即环境文件夹名，如 env_2896_prediction-trader），
便于 mcp_server.py 复制到其他环境时自动沿用新文件夹名。
"""

import json
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastmcp import FastMCP

try:
    # 同一环境内使用 LLM 生成工具回复与状态
    from . import llm_response
except Exception:  # pragma: no cover - 容错导入
    llm_response = None  # type: ignore[assignment]


# 轻量模式下的极简 KV 状态存储：单进程内存字典
_STATE_STORE: Dict[str, Dict[str, Any]] = {}
_DEFAULT_STATE_KEY = "default"


def _get_state(key: str = _DEFAULT_STATE_KEY) -> Dict[str, Any]:
    """获取当前会话状态（light 模式用）。"""
    return _STATE_STORE.get(key, {})


def _set_state(state: Dict[str, Any], key: str = _DEFAULT_STATE_KEY) -> None:
    """写回当前会话状态（light 模式用）。"""
    _STATE_STORE[key] = state or {}


def load_tool_module(tool_file: Path):
    """动态加载强状态环境下的工具模块。"""
    module_name = f"tools.{tool_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, tool_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def discover_tools(tools_dir: Path) -> Dict[str, Any]:
    """扫描并加载所有强状态工具（tools/*.py）。"""
    tools: Dict[str, Any] = {}

    for tool_file in tools_dir.glob("*.py"):
        # 跳过 __init__.py 和私有模块
        if tool_file.name.startswith("_") or tool_file.name.startswith("__"):
            continue

        try:
            module = load_tool_module(tool_file)

            # 检查是否有 TOOL_SCHEMA
            if hasattr(module, "TOOL_SCHEMA"):
                schema = module.TOOL_SCHEMA
                tools[schema["name"]] = {
                    "module": module,
                    "schema": schema,
                    "execute": module.execute,
                }
                print(f"Loaded tool: {schema['name']}")
            else:
                print(f"Warning: {tool_file.name} missing TOOL_SCHEMA")

        except Exception as e:  # pragma: no cover - 仅日志
            print(f"Error loading {tool_file.name}: {e}")

    return tools


def _wrap_execute_with_llm(tool_name: str, execute_fn):
    """
    strong 模式下：对真实 execute 结果做 LLM 文案增强。

    - 先调用 execute_fn(**kwargs) 获取 raw_result；
    - 若 llm_response 可用，则调用生成器，让其基于 tool_name / arguments / raw_result
      生成用户可见回复；失败时直接回退到 raw_result。
    - 这里暂不使用 KV 状态，仅做文案重写/补充解释。
    """

    def _handler(**kwargs):
        raw_result = execute_fn(**kwargs)
        # 若缺少 llm_response，则直接返回原始结果
        if llm_response is None:
            return raw_result
        try:
            args_json = json.dumps(kwargs or {}, ensure_ascii=False)
            out = llm_response.generate_tool_response(
                tool_name=tool_name,
                arguments_json=args_json,
                raw_result=str(raw_result),
                session_state=None,
                initial_state=None,
                conversation_context=None,
            )
            resp = (out.get("response") or "").strip()
            return resp or str(raw_result)
        except Exception as e:  # pragma: no cover - 容错回退
            print(f"[LLM wrapper] fallback to raw_result for {tool_name}: {e}")
            return raw_result

    return _handler


def create_mcp_tools_strong(mcp: FastMCP, tools: Dict[str, Any]) -> None:
    """strong 模式：基于 tools/*.py 注册 MCP 工具，使用 LLM 包裹执行结果。"""
    for tool_info in tools.values():
        schema = tool_info["schema"]
        execute = tool_info["execute"]

        handler = _wrap_execute_with_llm(schema["name"], execute)

        mcp.add_tool(
            handler,
            name=schema["name"],
            description=schema.get("description", ""),
        )


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


def _make_json_only_handler(tool_name: str):
    """
    轻量模式 handler：不执行真实工具，完全依赖 LLM 生成回复 + 状态。

    - 使用全局 KV 存储当前会话状态（单 key）。
    - 每次调用后写回新的完整状态。
    """

    def _handler(**kwargs):
        if llm_response is None:
            raise RuntimeError("llm_response 模块不可用，无法在 json-only 模式下生成工具回复")

        current_state = _get_state()
        args_json = json.dumps(kwargs or {}, ensure_ascii=False)
        out = llm_response.generate_tool_response(
            tool_name=tool_name,
            arguments_json=args_json,
            raw_result="",
            session_state=current_state,
            initial_state=None,
            conversation_context=None,
        )
        new_state = out.get("state")
        if isinstance(new_state, dict):
            _set_state(new_state)
        response = (out.get("response") or "").strip()
        return response or f"{tool_name} executed."

    return _handler


def create_mcp_tools_light(mcp: FastMCP, tools: List[Dict[str, Any]]) -> None:
    """light/json-only 模式：基于 tools.jsonl 注册通用 LLM 工具 handler。"""
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


def _select_env_mode(
    tools_dir: Path,
    tools_jsonl: Path,
) -> Tuple[str, Dict[str, Any]]:
    """
    根据 ENV_MODE 与实际文件选择运行模式。

    - ENV_MODE=strong：强制要求 tools/ 存在且可加载；
    - ENV_MODE=light：强制仅基于 tools.jsonl 注册工具；
    - ENV_MODE=auto（默认）：优先 strong（tools/ 存在且有 TOOL_SCHEMA），否则退回 light（tools.jsonl 存在）。
    """
    mode = os.environ.get("ENV_MODE", "auto").strip().lower() or "auto"

    strong_tools: Dict[str, Any] = {}
    if tools_dir.exists():
        strong_tools = discover_tools(tools_dir)

    has_strong = bool(strong_tools)
    has_jsonl = tools_jsonl.exists()

    if mode == "strong":
        if not has_strong:
            raise RuntimeError("ENV_MODE=strong，但未发现有效 tools/ 工具")
        return "strong", strong_tools

    if mode == "light":
        if not has_jsonl:
            raise RuntimeError("ENV_MODE=light，但未发现 tools.jsonl")
        return "light", {}

    # auto：优先 strong，其次 light
    if has_strong:
        return "strong", strong_tools
    if has_jsonl:
        return "light", {}

    raise RuntimeError("无法确定环境模式：既没有有效 tools/ 也没有 tools.jsonl")


def main():
    """主入口：MCP 名 = 当前目录名，支持 strong / light(json-only) 双模式。"""
    current_dir = Path(__file__).resolve().parent
    tools_dir = current_dir / "tools"
    tools_jsonl = current_dir / "tools.jsonl"
    mcp_name = current_dir.name

    print(f"{mcp_name} MCP Server")
    print(f"Tools directory: {tools_dir}")
    print(f"tools.jsonl: {tools_jsonl}")
    print("-" * 40)

    mode, strong_tools = _select_env_mode(tools_dir, tools_jsonl)
    print(f"ENV_MODE resolved to: {mode}")

    mcp = FastMCP(mcp_name)

    if mode == "strong":
        print(f"Loading strong tools from: {tools_dir}")
        print(f"Total tools loaded: {len(strong_tools)}")
        print("-" * 40)
        create_mcp_tools_strong(mcp, strong_tools)
    else:
        print(f"Loading light tools from: {tools_jsonl}")
        jsonl_tools = load_tools_from_jsonl(tools_jsonl)
        print(f"Total tools loaded from JSONL: {len(jsonl_tools)}")
        print("-" * 40)
        create_mcp_tools_light(mcp, jsonl_tools)

    # 启动服务：容器环境用 SSE 监听 8000（http/sse 均表示网络模式），本地默认 stdio
    print("\nStarting MCP server...")
    if os.environ.get("MCP_TRANSPORT") in ("http", "sse"):
        mcp.run(transport="sse")  # 使用 Settings 默认 host=0.0.0.0, port=8000
    else:
        mcp.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MCP 服务入口：扫描 tools/ 目录并注册所有工具。

服务名使用当前目录名（即环境文件夹名，如 env_2896_prediction-trader），
便于 mcp_server.py 复制到其他环境时自动沿用新文件夹名。
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Any, Dict

# MCP Server
from fastmcp import FastMCP


def load_tool_module(tool_file: Path):
    """动态加载工具模块"""
    module_name = f"tools.{tool_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, tool_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def discover_tools(tools_dir: Path) -> Dict[str, Any]:
    """扫描并加载所有工具"""
    tools = {}

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
                    "execute": module.execute
                }
                print(f"Loaded tool: {schema['name']}")
            else:
                print(f"Warning: {tool_file.name} missing TOOL_SCHEMA")

        except Exception as e:
            print(f"Error loading {tool_file.name}: {e}")

    return tools


def create_mcp_tools(mcp: FastMCP, tools: Dict[str, Any]):
    """为每个工具创建 MCP 端点"""

    for tool_info in tools.values():
        schema = tool_info["schema"]
        execute = tool_info["execute"]

        # 注册工具
        mcp.add_tool(
            execute,
            name=schema["name"],
            description=schema["description"],
        )


def main():
    """主入口：MCP 名 = 当前目录名，便于复制到任意环境目录后直接使用。"""
    current_dir = Path(__file__).resolve().parent
    tools_dir = current_dir / "tools"
    mcp_name = current_dir.name

    print(f"{mcp_name} MCP Server")
    print(f"Tools directory: {tools_dir}")
    print("-" * 40)

    tools = discover_tools(tools_dir)
    print(f"Total tools loaded: {len(tools)}")
    print("-" * 40)

    mcp = FastMCP(mcp_name)

    # 注册工具
    create_mcp_tools(mcp, tools)

    # 启动服务：容器环境用 SSE 监听 8000（http/sse 均表示网络模式），本地默认 stdio
    print("\nStarting MCP server...")
    if os.environ.get("MCP_TRANSPORT") in ("http", "sse"):
        mcp.run(transport="sse")  # 使用 Settings 默认 host=0.0.0.0, port=8000
    else:
        mcp.run()


if __name__ == "__main__":
    main()

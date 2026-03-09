#!/usr/bin/env python3
"""
Portfolio Risk Analyzer MCP Server

MCP 服务入口，扫描 tools/ 目录并注册所有工具。
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Any, Dict

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
        if tool_file.name.startswith("_") or tool_file.name.startswith("__"):
            continue

        try:
            module = load_tool_module(tool_file)

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

        except Exception as e:
            print(f"Error loading {tool_file.name}: {e}")

    return tools


def create_mcp_tools(mcp: FastMCP, tools: Dict[str, Any]):
    """为每个工具创建 MCP 端点"""

    for tool_info in tools.values():
        schema = tool_info["schema"]
        execute = tool_info["execute"]

        mcp.add_tool(
            execute,
            name=schema["name"],
            description=schema["description"],
        )


def main():
    """主入口"""
    current_dir = Path(__file__).parent
    tools_dir = current_dir / "tools"

    print(f"Portfolio Risk Analyzer MCP Server")
    print(f"Tools directory: {tools_dir}")
    print("-" * 40)

    tools = discover_tools(tools_dir)
    print(f"Total tools loaded: {len(tools)}")
    print("-" * 40)

    mcp = FastMCP("portfolio-risk-analyzer")

    create_mcp_tools(mcp, tools)

    print("\nStarting MCP server...")
    if os.environ.get("MCP_TRANSPORT") in ("http", "sse"):
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()

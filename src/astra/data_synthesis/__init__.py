"""
数据合成流水线：轻量 MCP 与 tools.jsonl 中心化逻辑。

提供 tools.jsonl 解析、LLM 工具回复生成、以及基于 FastMCP 的轻量 MCP 服务注册，
供环境生成与轨迹合成阶段复用。通过 Hydra 传入 tools_path 即可启动 MCP，无需 Docker。
"""

from astra.data_synthesis.tools_loader import load_tools_from_jsonl
from astra.data_synthesis.tool_response import generate_tool_response
from astra.data_synthesis.mcp_light import create_mcp_tools_light

__all__ = [
    "load_tools_from_jsonl",
    "generate_tool_response",
    "create_mcp_tools_light",
]

#!/usr/bin/env python3
"""
Test Tools - 快速测试所有 MCP 工具

运行所有工具的 execute() 函数进行冒烟测试。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

os.environ["POLYMARKET_API_BASE"] = "http://localhost:8001"


def test_tool(tool_module, tool_name):
    """测试单个工具"""
    print(f"\n{'=' * 50}")
    print(f"Testing: {tool_name}")
    print("=" * 50)

    try:
        if tool_name == "get_wallet_transactions":
            result = tool_module.execute(
                wallet_address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f", limit=5
            )
        elif tool_name == "get_wallet_positions":
            result = tool_module.execute(
                wallet_address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f"
            )
        elif tool_name == "get_trending_markets":
            result = tool_module.execute(limit=5)
        elif tool_name == "get_market_details":
            result = tool_module.execute(market_id="m1")
        elif tool_name == "list_known_whales":
            result = tool_module.execute(limit=5)
        elif tool_name == "simulate_copy_trade":
            result = tool_module.execute(
                whale_address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f",
                copy_percent=10,
                min_trade_usd=5,
                max_trade_usd=50,
            )
        elif tool_name == "get_copy_settings":
            result = tool_module.execute()
        else:
            print(f"Skipping {tool_name} - no test case")
            return

        print(result)
        print(f"\n[OK] {tool_name} passed")

    except Exception as e:
        print(f"\n[ERROR] {tool_name} failed: {e}")


def main():
    """主入口"""
    tools_dir = Path(__file__).parent / "tools"

    print("Testing all MCP tools...")
    print(f"Tools directory: {tools_dir}")

    tool_files = [
        "get_wallet_transactions",
        "get_wallet_positions",
        "get_trending_markets",
        "get_market_details",
        "list_known_whales",
        "simulate_copy_trade",
        "get_copy_settings",
    ]

    for tool_name in tool_files:
        tool_file = tools_dir / f"{tool_name}.py"

        if not tool_file.exists():
            print(f"Warning: {tool_file} not found")
            continue

        import importlib.util

        spec = importlib.util.spec_from_file_location(f"tools.{tool_name}", tool_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        test_tool(module, tool_name)

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()

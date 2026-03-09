"""
List Known Whales - 列出已知的 Polymarket 巨鲸钱包

返回 Polymarket 排行榜上的知名巨鲸钱包地址及其统计信息。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "list_known_whales",
    "description": "List known whale wallets from Polymarket leaderboard. "
    "These are top traders with profitable track records.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of whales to return",
            }
        },
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(limit: int = 10) -> str:
    """
    列出已知的巨鲸钱包

    Args:
        limit: 返回的最大数量

    Returns:
        格式化的巨鲸列表
    """
    try:
        url = f"{POLYMARKET_API_BASE}/leaderboard?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("traders"):
            return "No whale data available"

        output = "## Known Polymarket Whales\n\n"
        output += "*Top traders from Polymarket leaderboard*\n\n"

        for i, trader in enumerate(data["traders"], 1):
            output += f"### {i}. {trader.get('name', 'Anonymous')}\n"
            output += f"Address: `{trader.get('address', 'N/A')}`\n"
            output += f"- Profit: ${trader.get('profit', 0):,.2f}\n"
            output += f"- Win Rate: {trader.get('win_rate', 0) * 100:.1f}%\n"
            output += f"- Total Trades: {trader.get('total_trades', 0)}\n"
            output += f"- Volume: ${trader.get('volume', 0):,.2f}\n\n"

        return output

    except Exception as e:
        return f"Error fetching whale list: {str(e)}"


if __name__ == "__main__":
    print(execute())

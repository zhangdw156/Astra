"""
Get Trending Markets - 获取 Polymarket 热门市场

获取当前最活跃的 Polymarket 预测市场。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_trending_markets",
    "description": "Get trending prediction markets from Polymarket. "
    "Returns the most active markets with volume and price information.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of markets to return",
            }
        },
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(limit: int = 10) -> str:
    """
    获取热门市场

    Args:
        limit: 返回的最大市场数量

    Returns:
        格式化的热门市场数据
    """
    try:
        url = f"{POLYMARKET_API_BASE}/markets/trending?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("markets"):
            return "No trending markets found"

        output = "## Polymarket - Trending Markets\n\n"
        output += "*Offshore prediction market on Polygon*\n\n"

        for market in data["markets"]:
            output += f"**{market.get('question', 'N/A')}**\n"
            output += f"- YES: ${market.get('yes_price', 0):.2f} ({market.get('yes_price', 0) * 100:.0f}%)\n"
            output += (
                f"- NO: ${market.get('no_price', 0):.2f} ({market.get('no_price', 0) * 100:.0f}%)\n"
            )
            output += f"- Volume: ${market.get('volume', 0):,}\n"
            if market.get("end_date"):
                output += f"- Ends: {market.get('end_date')}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error fetching trending markets: {str(e)}"


if __name__ == "__main__":
    print(execute())

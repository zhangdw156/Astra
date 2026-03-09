"""
Trending Tool - 获取两个平台的热门预测市场

同时获取 Polymarket 和 Kalshi 的热门预测市场。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "trending",
    "description": "Get trending prediction markets from both Polymarket and Kalshi. "
                   "Polymarket is an offshore market (crypto, politics, sports). "
                   "Kalshi is a CFTC-regulated US market (economics, Fed rates). "
                   "This tool aggregates trending markets from both platforms.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of markets per platform"
            }
        }
    }
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(limit: int = 5) -> str:
    """
    获取两个平台的热门预测市场

    Args:
        limit: 每个平台返回的数量

    Returns:
        格式化的热门市场数据
    """
    output = "## Trending Prediction Markets\n\n"

    # 获取 Polymarket trending
    try:
        url = f"{UNIFAI_API_BASE}/v1/agent/trending"
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Polymarket - Trending Events\n"
        output += "*Offshore prediction market on Polygon*\n\n"

        if data.get("data"):
            for event in data["data"]["events"][:limit]:
                output += f"- **{event['question']}**\n"
                output += f"  YES: ${event['yes']:.2f} | NO: ${event['no']:.2f} | Vol: {event['volume']}\n\n"

    except Exception as e:
        output += f"Error fetching Polymarket trending: {str(e)}\n\n"

    # 获取 Kalshi trending
    try:
        url = f"{KALSHI_API_BASE}/markets/trending?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Kalshi - High Volume Markets\n"
        output += "*CFTC-regulated US prediction market*\n\n"

        if data.get("markets"):
            for m in data["markets"]:
                output += f"- **{m['title']}**\n"
                output += f"  YES: ${m['yes_price']:.2f} | NO: ${m['no_price']:.2f} | Vol: ${m['volume']:,}\n\n"

    except Exception as e:
        output += f"Error fetching Kalshi trending: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute(3))

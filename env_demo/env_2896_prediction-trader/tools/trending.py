"""
Trending Tool - 获取热门预测市场

获取两个平台上最热门的预测市场。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "trending",
    "description": "Get trending prediction markets from both Polymarket and Kalshi. "
    "Shows the most active and highest volume markets across both platforms.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of markets per platform",
            }
        },
    },
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(limit: int = 10) -> str:
    """
    获取热门预测市场

    Args:
        limit: 每个平台返回的数量

    Returns:
        格式化的热门市场结果
    """
    output = "## Trending Prediction Markets\n\n"

    # 获取 Kalshi trending
    try:
        url = f"{KALSHI_API_BASE}/markets/trending?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Kalshi - High Volume Markets\n\n"

        if data.get("markets"):
            for m in data["markets"][:limit]:
                output += f"**{m['title']}**\n"
                output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price'] * 100:.0f}%)\n"
                output += f"- NO: ${m['no_price']:.2f} ({m['no_price'] * 100:.0f}%)\n"
                output += f"- Volume: ${m['volume']:,}\n\n"
        else:
            output += "No trending markets found\n\n"

    except Exception as e:
        output += f"Error fetching Kalshi trending: {str(e)}\n\n"

    # 获取 Polymarket trending
    try:
        url = f"{UNIFAI_API_BASE}/v1/agent/trending"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Polymarket - Trending Events\n\n"

        if data.get("data", {}).get("events"):
            for event in data["data"]["events"][:limit]:
                output += f"**{event['question']}**\n"
                output += f"- YES: ${event['yes']:.2f} | NO: ${event['no']:.2f}\n"
                output += f"- Volume: {event['volume']}\n\n"
        else:
            output += "No trending events found\n\n"

    except Exception as e:
        output += f"Error fetching Polymarket trending: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Polymarket Trending Tool - 获取 Polymarket 热门市场

获取 Polymarket 平台上最热门的预测市场事件。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "polymarket_trending",
    "description": "Get trending prediction markets from Polymarket. "
    "Polymarket is an offshore prediction market on Polygon (crypto, politics, sports, world events).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of trending events to return",
            }
        },
    },
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(limit: int = 10) -> str:
    """
    获取 Polymarket 热门市场

    Args:
        limit: 返回的事件数量

    Returns:
        格式化的热门市场结果
    """
    output = "## Polymarket Trending Markets\n\n"

    try:
        url = f"{UNIFAI_API_BASE}/v1/agent/trending"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("data", {}).get("events"):
            for event in data["data"]["events"][:limit]:
                output += f"**{event['question']}**\n"
                output += f"- YES: ${event['yes']:.2f} ({event['yes'] * 100:.0f}%)\n"
                output += f"- NO: ${event['no']:.2f} ({event['no'] * 100:.0f}%)\n"
                output += f"- Volume: {event['volume']}\n"
                if event.get("description"):
                    output += f"- {event['description']}\n"
                output += "\n"
        else:
            output += "No trending events found.\n"

    except Exception as e:
        output += f"Error fetching Polymarket trending: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Compare Markets Tool - 比较两个平台的预测市场

比较特定主题在 Polymarket 和 Kalshi 上的预测市场。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "compare_markets",
    "description": "Compare prediction markets for a specific topic across both Polymarket and Kalshi. "
    "Polymarket is an offshore market (crypto, politics, sports). "
    "Kalshi is a CFTC-regulated US market (economics, Fed rates). "
    "Use this to compare odds and find arbitrage opportunities.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic to compare (e.g., 'bitcoin', 'fed rate', 'election')",
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of markets per platform",
            },
        },
        "required": ["topic"],
    },
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(topic: str, limit: int = 5) -> str:
    """
    比较两个平台的预测市场

    Args:
        topic: 比较主题
        limit: 每个平台返回的数量

    Returns:
        格式化的比较结果
    """
    output = f"## Prediction Markets: {topic}\n\n"

    # 搜索 Kalshi
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{KALSHI_API_BASE}/markets/search?q={encoded_topic}&limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Kalshi (CFTC-Regulated)\n\n"

        if data.get("markets"):
            for m in data["markets"]:
                output += f"**{m['title']}**\n"
                output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price'] * 100:.0f}%)\n"
                output += f"- NO: ${m['no_price']:.2f} ({m['no_price'] * 100:.0f}%)\n"
                output += f"- Volume: ${m['volume']:,}\n\n"
        else:
            output += "No markets found\n\n"

    except Exception as e:
        output += f"Error searching Kalshi: {str(e)}\n\n"

    # 搜索 Polymarket
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{UNIFAI_API_BASE}/v1/agent/search?q={encoded_topic}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "### Polymarket\n\n"

        if data.get("response"):
            output += data["response"] + "\n\n"
        else:
            output += "No markets found\n\n"

    except Exception as e:
        output += f"Error searching Polymarket: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

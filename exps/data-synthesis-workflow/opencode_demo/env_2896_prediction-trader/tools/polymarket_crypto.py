"""
Polymarket Crypto Tool - 获取Polymarket加密货币预测市场

Polymarket 是一个基于 Polygon 的离岸预测市场，提供加密货币价格预测。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "polymarket_crypto",
    "description": "Get cryptocurrency prediction markets from Polymarket. "
                   "Polymarket is an offshore prediction market on Polygon with crypto price predictions. "
                   "Returns crypto-related prediction markets (Bitcoin, Ethereum, etc.).",
    "inputSchema": {
        "type": "object",
        "properties": {}
    }
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute() -> str:
    """
    获取Polymarket加密货币预测市场

    Returns:
        格式化的加密货币市场数据
    """
    try:
        url = f"{UNIFAI_API_BASE}/v1/agent/crypto"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("data"):
            return "No crypto markets found"

        events = data["data"]["events"]
        output = "## Polymarket - Cryptocurrency Markets\n\n"
        output += "*Offshore prediction market on Polygon*\n\n"

        for event in events:
            output += f"**{event['question']}**\n"
            output += f"- YES: ${event['yes']:.2f} ({event['yes']*100:.0f}%)\n"
            output += f"- NO: ${event['no']:.2f} ({event['no']*100:.0f}%)\n"
            output += f"- Volume: {event['volume']}\n"
            if event.get("description"):
                output += f"- {event['description']}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error fetching crypto markets: {str(e)}"


if __name__ == "__main__":
    print(execute())

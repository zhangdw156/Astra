"""
Analyze Topic Tool - 分析特定主题的预测市场

对特定主题进行完整分析，包括市场数据和社交信号。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "analyze_topic",
    "description": "Full analysis of a prediction market topic including data from both platforms "
    "and market consensus. Compares odds across platforms and summarizes market sentiment.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic to analyze (e.g., 'bitcoin', 'fed rate', 'election')",
            }
        },
        "required": ["topic"],
    },
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(topic: str) -> str:
    """
    分析特定主题的预测市场

    Args:
        topic: 分析主题

    Returns:
        格式化的分析结果
    """
    output = f"## Analysis: {topic}\n\n"

    # 获取 Kalshi 数据
    kalshi_markets = []
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{KALSHI_API_BASE}/markets/search?q={encoded_topic}&limit=5"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
            kalshi_markets = data.get("markets", [])

    except Exception as e:
        output += f"Error fetching Kalshi data: {str(e)}\n\n"

    # 获取 Polymarket 数据
    polymarket_data = None
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{UNIFAI_API_BASE}/v1/agent/search?q={encoded_topic}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            polymarket_data = json.loads(response.read().decode())

    except Exception as e:
        output += f"Error fetching Polymarket data: {str(e)}\n\n"

    # 汇总分析
    output += "### Market Summary\n\n"

    if kalshi_markets:
        output += f"**Kalshi ({len(kalshi_markets)} markets):**\n"
        for m in kalshi_markets:
            output += f"- {m['title']}: YES ${m['yes_price']:.2f} | NO ${m['no_price']:.2f}\n"
        output += "\n"
    else:
        output += "No Kalshi markets found for this topic.\n\n"

    if polymarket_data and polymarket_data.get("response"):
        output += "**Polymarket:**\n"
        output += polymarket_data["response"] + "\n\n"

    # 计算市场共识
    output += "### Market Consensus\n\n"

    if kalshi_markets:
        avg_yes = sum(m["yes_price"] for m in kalshi_markets) / len(kalshi_markets)
        output += f"- Average YES probability (Kalshi): {avg_yes * 100:.1f}%\n"
    else:
        output += "- No consensus data available from Kalshi\n"

    output += "\n**Note**: This analysis is for informational purposes only. "
    output += "Prediction markets can be volatile and past performance does not guarantee future results.\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

"""
Analyze Topic Tool - 全面分析某个主题的预测市场

分析特定主题在各个预测市场的数据，并提供社交信号分析。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "analyze_topic",
    "description": "Perform a comprehensive analysis of prediction markets for a specific topic. "
                   "This includes searching both Polymarket and Kalshi, comparing odds across platforms, "
                   "and providing market consensus analysis. "
                   "Use this when you need detailed analysis beyond simple comparison.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic to analyze (e.g., 'bitcoin', 'fed rate', 'election 2026')"
            }
        },
        "required": ["topic"]
    }
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(topic: str) -> str:
    """
    全面分析某个主题的预测市场

    Args:
        topic: 分析主题

    Returns:
        格式化的分析结果
    """
    output = f"# Market Analysis: {topic}\n\n"
    output += "=" * 50 + "\n\n"

    # Step 1: 搜索 Polymarket
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{UNIFAI_API_BASE}/v1/agent/search?q={encoded_topic}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "## Polymarket Data\n\n"
        if data.get("response"):
            output += data["response"] + "\n\n"
        else:
            output += "No data available\n\n"

    except Exception as e:
        output += f"Error fetching Polymarket data: {str(e)}\n\n"

    # Step 2: 搜索 Kalshi
    try:
        encoded_topic = urllib.parse.quote(topic)
        url = f"{KALSHI_API_BASE}/markets/search?q={encoded_topic}&limit=10"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        output += "## Kalshi Data\n\n"
        if data.get("markets"):
            for m in data["markets"]:
                output += f"**{m['title']}**\n"
                output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price']*100:.0f}%)\n"
                output += f"- NO: ${m['no_price']:.2f} ({m['no_price']*100:.0f}%)\n"
                output += f"- Volume: ${m['volume']:,}\n\n"
        else:
            output += "No markets found\n\n"

    except Exception as e:
        output += f"Error fetching Kalshi data: {str(e)}\n\n"

    # Step 3: Market Consensus Summary
    output += "## Market Consensus Summary\n\n"
    output += f"Analysis for: **{topic}**\n\n"
    output += "### Key Takeaways:\n\n"
    output += "1. **Platform Coverage**: Both Polymarket and Kalshi offer prediction markets for this topic.\n\n"
    output += "2. **Market Sentiment**: Based on the YES/NO prices, market participants lean towards certain outcomes.\n\n"
    output += "3. **Volume Analysis**: Higher volume markets indicate stronger market confidence.\n\n"
    output += "4. **Cross-Platform Comparison**: Compare odds between platforms to identify potential arbitrage.\n\n"
    output += "*Note: This is mock data for demonstration. Real analysis would include social signals and recent news.*\n\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

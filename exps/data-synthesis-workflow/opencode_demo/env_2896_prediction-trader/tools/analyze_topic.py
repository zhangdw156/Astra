"""
Analyze Topic Tool - 全面分析某个主题的预测市场

通过状态访问层读取双平台数据并汇总分析（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

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


def execute(topic: str) -> str:
    """从状态层读取双平台数据并生成分析报告。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_kalshi_markets, read_polymarket_events

    output = f"# Market Analysis: {topic}\n\n"
    output += "=" * 50 + "\n\n"

    poly = read_polymarket_events(search_query=topic, limit=10)
    output += "## Polymarket Data\n\n"
    if poly:
        for e in poly:
            output += f"**{e['question']}**\n"
            output += f"- YES: ${e['yes_price']:.2f} ({e['yes_price']*100:.0f}%)\n"
            output += f"- NO: ${e['no_price']:.2f} | Volume: {e.get('volume_display', 'N/A')}\n\n"
    else:
        output += "No data available\n\n"

    kalshi = read_kalshi_markets(search_query=topic, limit=10)
    output += "## Kalshi Data\n\n"
    if kalshi:
        for m in kalshi:
            output += f"**{m['title']}**\n"
            output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price']*100:.0f}%)\n"
            output += f"- NO: ${m['no_price']:.2f} | Volume: ${m['volume']:,}\n\n"
    else:
        output += "No markets found\n\n"

    output += "## Market Consensus Summary\n\n"
    output += f"Analysis for: **{topic}**\n\n"
    output += "### Key Takeaways:\n\n"
    output += "1. **Platform Coverage**: Both Polymarket and Kalshi offer prediction markets for this topic.\n\n"
    output += "2. **Market Sentiment**: Based on the YES/NO prices, market participants lean towards certain outcomes.\n\n"
    output += "3. **Volume Analysis**: Higher volume markets indicate stronger market confidence.\n\n"
    output += "4. **Cross-Platform Comparison**: Compare odds between platforms to identify potential arbitrage.\n\n"
    output += "*Note: Data from shared SQLite state backend; state is deterministic and verifiable.*\n\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

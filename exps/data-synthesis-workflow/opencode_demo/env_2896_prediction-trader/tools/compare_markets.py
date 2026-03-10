"""
Compare Markets Tool - 比较两个平台的预测市场

通过状态访问层按主题搜索 Kalshi 与 Polymarket（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

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
                "description": "Topic to compare (e.g., 'bitcoin', 'fed rate', 'election')"
            },
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Maximum number of markets per platform"
            }
        },
        "required": ["topic"]
    }
}


def execute(topic: str, limit: int = 5) -> str:
    """从状态层按 topic 比较两平台市场。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_kalshi_markets, read_polymarket_events

    output = f"## Prediction Markets: {topic}\n\n"

    kalshi = read_kalshi_markets(search_query=topic, limit=limit)
    output += "### Kalshi (CFTC-Regulated)\n\n"
    if kalshi:
        for m in kalshi:
            output += f"**{m['title']}**\n"
            output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price']*100:.0f}%)\n"
            output += f"- NO: ${m['no_price']:.2f} ({m['no_price']*100:.0f}%)\n"
            output += f"- Volume: ${m['volume']:,}\n\n"
    else:
        output += "No markets found\n\n"

    poly = read_polymarket_events(search_query=topic, limit=limit)
    output += "### Polymarket\n\n"
    if poly:
        for e in poly:
            output += f"**{e['question']}**\n"
            output += f"- YES: ${e['yes_price']:.2f} ({e['yes_price']*100:.0f}%)\n"
            output += f"- NO: ${e['no_price']:.2f} ({e['no_price']*100:.0f}%)\n"
            output += f"- Volume: {e.get('volume_display', 'N/A')}\n\n"
    else:
        output += "No markets found\n\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

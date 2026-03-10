"""
Trending Tool - 获取两个平台的热门预测市场

通过状态访问层同时读取 Polymarket 与 Kalshi（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

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


def execute(limit: int = 5) -> str:
    """从状态层读取双平台热门市场。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_polymarket_events, read_kalshi_markets

    output = "## Trending Prediction Markets\n\n"

    poly = read_polymarket_events(category="trending", limit=limit)
    output += "### Polymarket - Trending Events\n"
    output += "*Offshore prediction market on Polygon*\n\n"
    if poly:
        for e in poly:
            output += f"- **{e['question']}**\n"
            output += f"  YES: ${e['yes_price']:.2f} | NO: ${e['no_price']:.2f} | Vol: {e.get('volume_display', 'N/A')}\n\n"
    else:
        output += "No trending markets\n\n"

    kalshi = read_kalshi_markets(category="trending", limit=limit)
    output += "### Kalshi - High Volume Markets\n"
    output += "*CFTC-regulated US prediction market*\n\n"
    if kalshi:
        for m in kalshi:
            output += f"- **{m['title']}**\n"
            output += f"  YES: ${m['yes_price']:.2f} | NO: ${m['no_price']:.2f} | Vol: ${m['volume']:,}\n\n"
    else:
        output += "No trending markets\n"

    return output


if __name__ == "__main__":
    print(execute(3))

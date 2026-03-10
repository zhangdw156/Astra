"""
Polymarket Trending Tool - 获取 Polymarket 热门预测市场

通过状态访问层读取（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

TOOL_SCHEMA = {
    "name": "polymarket_trending",
    "description": "Get trending prediction markets from Polymarket. "
                   "Polymarket is an offshore prediction market on Polygon covering crypto, politics, sports, and world events. "
                   "Returns the most active and discussed prediction markets.",
    "inputSchema": {
        "type": "object",
        "properties": {}
    }
}


def execute() -> str:
    """从状态层读取 Polymarket 热门事件。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_polymarket_events

    events = read_polymarket_events(category="trending")
    if not events:
        return "No trending markets found"

    output = "## Polymarket - Trending Events\n\n"
    output += "*Offshore prediction market on Polygon*\n\n"
    for e in events:
        output += f"**{e['question']}**\n"
        output += f"- YES: ${e['yes_price']:.2f} ({e['yes_price']*100:.0f}%)\n"
        output += f"- NO: ${e['no_price']:.2f} ({e['no_price']*100:.0f}%)\n"
        output += f"- Volume: {e.get('volume_display', 'N/A')}\n"
        if e.get("description"):
            output += f"- {e['description']}\n"
        output += "\n"
    return output


if __name__ == "__main__":
    print(execute())

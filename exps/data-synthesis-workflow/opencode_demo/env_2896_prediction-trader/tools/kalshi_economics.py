"""
Kalshi Economics Markets Tool - 获取经济相关预测市场

通过状态访问层读取（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

TOOL_SCHEMA = {
    "name": "kalshi_economics",
    "description": "Get economics prediction markets from Kalshi (GDP, CPI, inflation). "
                   "Kalshi is a CFTC-regulated US prediction market with economic forecasts.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of markets to return"
            }
        }
    }
}


def execute(limit: int = 10) -> str:
    """从状态层读取经济预测市场。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_kalshi_markets

    markets = read_kalshi_markets(category="economics", limit=limit)
    if not markets:
        return "No economics markets found"

    output = "## Economics Markets - GDP/CPI (Kalshi)\n\n"
    output += "*CFTC-regulated US prediction market*\n\n"
    for m in markets:
        yes_pct = m["yes_price"] * 100
        output += f"**{m['title']}**\n"
        output += f"- YES: ${m['yes_price']:.2f} ({yes_pct:.0f}%)\n"
        output += f"- NO: ${m['no_price']:.2f} ({100-yes_pct:.0f}%)\n"
        output += f"- Volume: ${m['volume']:,}\n"
        if m.get("close_date"):
            output += f"- Closes: {m['close_date'][:10]}\n"
        output += "\n"
    return output


if __name__ == "__main__":
    print(execute(5))

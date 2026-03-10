"""
Kalshi Fed Markets Tool - 获取美联储利率相关预测市场

通过状态访问层读取 SQLite，与 Mock 共享同一状态后端（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

TOOL_SCHEMA = {
    "name": "kalshi_fed",
    "description": "Get Federal Reserve interest rate prediction markets from Kalshi. "
                   "Kalshi is a CFTC-regulated US prediction market. "
                   "This tool returns current Fed rate prediction markets including probability of rate cuts.",
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
    """从状态层读取美联储利率预测市场并格式化输出。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_kalshi_markets

    markets = read_kalshi_markets(category="fed", limit=limit)
    if not markets:
        return "No Fed markets found"

    output = "## Federal Reserve Interest Rate Markets (Kalshi)\n\n"
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

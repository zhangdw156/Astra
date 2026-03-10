"""
Kalshi Search Tool - 搜索 Kalshi 预测市场

通过状态访问层按 title 模糊查询（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

TOOL_SCHEMA = {
    "name": "kalshi_search",
    "description": "Search for prediction markets on Kalshi by query. "
                   "Kalshi is a CFTC-regulated US prediction market covering economics, politics, and more.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'bitcoin', 'election', 'fed')"
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of results"
            }
        },
        "required": ["query"]
    }
}


def execute(query: str, limit: int = 10) -> str:
    """从状态层搜索 Kalshi 市场。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_kalshi_markets

    markets = read_kalshi_markets(search_query=query, limit=limit)
    if not markets:
        return f"No markets found for query: {query}"

    output = f"## Kalshi Search: {query}\n\n"
    output += f"*Found {len(markets)} markets*\n\n"
    for m in markets:
        yes_pct = m["yes_price"] * 100
        output += f"**{m['title']}**\n"
        output += f"- YES: ${m['yes_price']:.2f} ({yes_pct:.0f}%)\n"
        output += f"- NO: ${m['no_price']:.2f} ({100-yes_pct:.0f}%)\n"
        output += f"- Volume: ${m['volume']:,}\n\n"
    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

"""
Polymarket Search Tool - 在 Polymarket 搜索预测市场

通过状态访问层按 question 模糊查询（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

TOOL_SCHEMA = {
    "name": "polymarket_search",
    "description": "Search for prediction markets on Polymarket by query. "
                   "Polymarket is an offshore prediction market on Polygon. "
                   "Search for specific topics like 'bitcoin', 'election', 'fed', 'AI', etc.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'bitcoin', 'election', 'fed rate', 'AI')"
            }
        },
        "required": ["query"]
    }
}


def execute(query: str) -> str:
    """从状态层搜索 Polymarket 并返回格式化文本（与 UnifAI 搜索风格一致）。"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from state import read_polymarket_events, read_kalshi_markets

    poly = read_polymarket_events(search_query=query, limit=10)
    kalshi = read_kalshi_markets(search_query=query, limit=5)

    lines = [f"**Polymarket Search: {query}**\n"]
    if poly:
        lines.append("| Question | Yes | No | Volume |")
        lines.append("|----------|-----|-----|--------|")
        for e in poly[:5]:
            lines.append(f"| {e['question'][:50]} | ${e['yes_price']:.2f} | ${e['no_price']:.2f} | {e.get('volume_display', '')} |")
    if kalshi:
        lines.append("\n**Kalshi** (CFTC-regulated)\n")
        for m in kalshi:
            lines.append(f"- {m['title']} | YES ${m['yes_price']:.2f} | Vol ${m['volume']:,}")
    if not poly and not kalshi:
        return f"No results found for query: {query}"
    lines.append("\n**Summary**: Data from shared state database.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(execute("bitcoin"))

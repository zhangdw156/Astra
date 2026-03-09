"""
Kalshi Search Tool - 搜索Kalshi预测市场

在Kalshi预测市场中搜索特定主题的市场。
"""

import json
import os
import urllib.request
import urllib.parse

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

KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(query: str, limit: int = 10) -> str:
    """
    搜索Kalshi预测市场

    Args:
        query: 搜索关键词
        limit: 最大返回数量

    Returns:
        格式化的搜索结果
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{KALSHI_API_BASE}/markets/search?q={encoded_query}&limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("markets"):
            return f"No markets found for query: {query}"

        # 格式化输出
        output = f"## Kalshi Search: {query}\n\n"
        output += f"*Found {data['total']} markets*\n\n"

        for m in data["markets"]:
            yes_pct = m["yes_price"] * 100
            output += f"**{m['title']}**\n"
            output += f"- YES: ${m['yes_price']:.2f} ({yes_pct:.0f}%)\n"
            output += f"- NO: ${m['no_price']:.2f} ({100-yes_pct:.0f}%)\n"
            output += f"- Volume: ${m['volume']:,}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error searching markets: {str(e)}"


if __name__ == "__main__":
    print(execute("bitcoin"))

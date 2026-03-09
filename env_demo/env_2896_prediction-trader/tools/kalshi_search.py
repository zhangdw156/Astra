"""
Kalshi Search Tool - 搜索经济预测市场

在 Kalshi 平台上搜索特定主题的预测市场。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "kalshi_search",
    "description": "Search for prediction markets on Kalshi by query. "
    "Kalshi is a CFTC-regulated US prediction market (Fed rates, GDP, CPI, economics).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'fed rate', 'GDP', 'CPI', 'unemployment')",
            },
            "limit": {"type": "integer", "default": 10, "description": "Maximum number of results"},
        },
        "required": ["query"],
    },
}

KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(query: str, limit: int = 10) -> str:
    """
    搜索 Kalshi 市场

    Args:
        query: 搜索关键词
        limit: 返回结果数量

    Returns:
        格式化的搜索结果
    """
    output = f"## Kalshi Search: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{KALSHI_API_BASE}/markets/search?q={encoded_query}&limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("markets"):
            for m in data["markets"]:
                output += f"**{m['title']}**\n"
                output += f"- YES: ${m['yes_price']:.2f} ({m['yes_price'] * 100:.0f}%)\n"
                output += f"- NO: ${m['no_price']:.2f} ({m['no_price'] * 100:.0f}%)\n"
                output += f"- Volume: ${m['volume']:,}\n"
                if m.get("closeDate"):
                    output += f"- Resolution: {m['closeDate'][:10]}\n"
                output += "\n"
        else:
            output += "No markets found.\n"

    except Exception as e:
        output += f"Error searching Kalshi: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("fed rate"))

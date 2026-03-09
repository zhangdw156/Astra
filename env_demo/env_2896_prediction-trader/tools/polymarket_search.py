"""
Polymarket Search Tool - 搜索 Polymarket 预测市场

在 Polymarket 平台上搜索特定主题的预测市场。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "polymarket_search",
    "description": "Search for prediction markets on Polymarket by query. "
    "Polymarket is an offshore prediction market on Polygon (crypto, politics, sports).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'bitcoin', 'election', 'fed rate')",
            },
            "limit": {"type": "integer", "default": 10, "description": "Maximum number of results"},
        },
        "required": ["query"],
    },
}

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(query: str, limit: int = 10) -> str:
    """
    搜索 Polymarket 市场

    Args:
        query: 搜索关键词
        limit: 返回结果数量

    Returns:
        格式化的搜索结果
    """
    output = f"## Polymarket Search: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{UNIFAI_API_BASE}/v1/agent/search?q={encoded_query}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("response"):
            output += data["response"] + "\n"
        else:
            output += "No markets found.\n"

    except Exception as e:
        output += f"Error searching Polymarket: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

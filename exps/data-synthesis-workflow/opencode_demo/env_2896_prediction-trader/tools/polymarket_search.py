"""
Polymarket Search Tool - 在Polymarket搜索预测市场

在Polymarket预测市场中搜索特定主题。
"""

import json
import os
import urllib.request
import urllib.parse

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

UNIFAI_API_BASE = os.environ.get("UNIFAI_API_BASE", "http://localhost:8001")
UNIFAI_API_KEY = os.environ.get("UNIFAI_AGENT_API_KEY", "mock-api-key")


def execute(query: str) -> str:
    """
    在Polymarket搜索预测市场

    Args:
        query: 搜索关键词

    Returns:
        格式化的搜索结果
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{UNIFAI_API_BASE}/v1/agent/search?q={encoded_query}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {UNIFAI_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("response"):
            return f"No results found for query: {query}"

        return data["response"]

    except Exception as e:
        return f"Error searching Polymarket: {str(e)}"


if __name__ == "__main__":
    print(execute("bitcoin"))

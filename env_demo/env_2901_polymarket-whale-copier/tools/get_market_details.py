"""
Get Market Details - 获取 Polymarket 市场详情

获取特定预测市场的详细信息。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_market_details",
    "description": "Get detailed information for a specific Polymarket market. "
    "Returns market question, prices, volume, and other details.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market_id": {"type": "string", "description": "Polymarket market ID (UUID format)"}
        },
        "required": ["market_id"],
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(market_id: str) -> str:
    """
    获取市场详情

    Args:
        market_id: 市场 ID

    Returns:
        格式化的市场详情
    """
    try:
        encoded_id = urllib.parse.quote(market_id)
        url = f"{POLYMARKET_API_BASE}/markets/{encoded_id}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        market = data.get("market", {})

        output = f"## Market Details\n\n"
        output += f"**Question:** {market.get('question', 'N/A')}\n\n"
        output += f"### Prices\n"
        output += (
            f"- YES: ${market.get('yes_price', 0):.2f} ({market.get('yes_price', 0) * 100:.0f}%)\n"
        )
        output += (
            f"- NO: ${market.get('no_price', 0):.2f} ({market.get('no_price', 0) * 100:.0f}%)\n\n"
        )
        output += f"### Volume\n"
        output += f"- Total Volume: ${market.get('volume', 0):,}\n"
        output += f"- Open Interest: ${market.get('open_interest', 0):,}\n\n"

        if market.get("description"):
            output += f"### Description\n{market.get('description')}\n\n"

        if market.get("end_date"):
            output += f"**End Date:** {market.get('end_date')}\n"

        if market.get("outcome_type"):
            output += f"**Outcome Type:** {market.get('outcome_type')}\n"

        if market.get("group_item_title"):
            output += f"**Category:** {market.get('group_item_title')}\n"

        return output

    except Exception as e:
        return f"Error fetching market details: {str(e)}"


if __name__ == "__main__":
    print(execute("abc123"))

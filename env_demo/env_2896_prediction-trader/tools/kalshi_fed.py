"""
Kalshi Fed Tool - 获取美联储利率预测市场

获取 Kalshi 平台上的美联储相关预测市场（利率、货币政策等）。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "kalshi_fed",
    "description": "Get Federal Reserve interest rate prediction markets from Kalshi. "
    "Kalshi is a CFTC-regulated US prediction market (economics, Fed rates).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of Fed markets to return",
            }
        },
    },
}

KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(limit: int = 10) -> str:
    """
    获取美联储利率市场

    Args:
        limit: 返回的市场数量

    Returns:
        格式化的美联储市场结果
    """
    output = "## Federal Reserve Interest Rate Markets (Kalshi)\n\n"

    try:
        url = f"{KALSHI_API_BASE}/markets/fed?limit={limit}"

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
            output += "No Fed markets found.\n"

    except Exception as e:
        output += f"Error fetching Fed markets: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Kalshi Economics Tool - 获取经济预测市场

获取 Kalshi 平台上的经济相关预测市场（GDP、CPI等）。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "kalshi_economics",
    "description": "Get economics prediction markets from Kalshi. "
    "Includes GDP, CPI, unemployment and other US economic indicators.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of economics markets to return",
            }
        },
    },
}

KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(limit: int = 10) -> str:
    """
    获取经济预测市场

    Args:
        limit: 返回的市场数量

    Returns:
        格式化的经济市场结果
    """
    output = "## Economics Markets - GDP/CPI (Kalshi)\n\n"

    try:
        url = f"{KALSHI_API_BASE}/markets/economics?limit={limit}"

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
            output += "No economics markets found.\n"

    except Exception as e:
        output += f"Error fetching economics markets: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

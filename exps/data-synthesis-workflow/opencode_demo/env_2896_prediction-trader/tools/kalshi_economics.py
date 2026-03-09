"""
Kalshi Economics Markets Tool - 获取经济相关预测市场

Kalshi 是 CFTC 监管的美国预测市场，提供GDP、CPI等经济预测。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "kalshi_economics",
    "description": "Get economics prediction markets from Kalshi (GDP, CPI, inflation). "
                   "Kalshi is a CFTC-regulated US prediction market with economic forecasts.",
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

KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(limit: int = 10) -> str:
    """
    获取经济预测市场

    Args:
        limit: 最大返回数量

    Returns:
        格式化的市场数据
    """
    try:
        url = f"{KALSHI_API_BASE}/markets/economics?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("markets"):
            return "No economics markets found"

        # 格式化输出
        output = "## Economics Markets - GDP/CPI (Kalshi)\n\n"
        output += "*CFTC-regulated US prediction market*\n\n"

        for m in data["markets"]:
            yes_pct = m["yes_price"] * 100
            output += f"**{m['title']}**\n"
            output += f"- YES: ${m['yes_price']:.2f} ({yes_pct:.0f}%)\n"
            output += f"- NO: ${m['no_price']:.2f} ({100-yes_pct:.0f}%)\n"
            output += f"- Volume: ${m['volume']:,}\n"
            if m.get("closeDate"):
                output += f"- Closes: {m['closeDate'][:10]}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error fetching economics markets: {str(e)}"


if __name__ == "__main__":
    print(execute(5))

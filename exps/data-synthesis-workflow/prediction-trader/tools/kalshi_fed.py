"""
Kalshi Fed Markets Tool - 获取美联储利率相关预测市场

Kalshi 是 CFTC 监管的美国预测市场，提供美联储利率、GDP、CPI等经济预测。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "kalshi_fed",
    "description": "Get Federal Reserve interest rate prediction markets from Kalshi. "
                   "Kalshi is a CFTC-regulated US prediction market. "
                   "This tool returns current Fed rate prediction markets including probability of rate cuts.",
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

# 默认使用 Mock API
KALSHI_API_BASE = os.environ.get("KALSHI_API_BASE", "http://localhost:8002")


def execute(limit: int = 10) -> str:
    """
    获取美联储利率预测市场

    Args:
        limit: 最大返回数量

    Returns:
        格式化的市场数据
    """
    try:
        url = f"{KALSHI_API_BASE}/markets/fed?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("markets"):
            return "No Fed markets found"

        # 格式化输出
        output = "## Federal Reserve Interest Rate Markets (Kalshi)\n\n"
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
        return f"Error fetching Fed markets: {str(e)}"


if __name__ == "__main__":
    print(execute(5))

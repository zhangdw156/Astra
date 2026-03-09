"""
Get Stock Price Tool - 获取单只股票当前价格

获取特定股票代码的实时价格。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_stock_price",
    "description": "Get current price for a specific stock symbol. Supports A-shares (.SS, .SZ), HK stocks (.HK), and US stocks.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock symbol (e.g., 600519.SS for Kweichow Moutai, 0700.HK for Tencent, AAPL for Apple)",
            }
        },
        "required": ["symbol"],
    },
}

STOCK_API_BASE = os.environ.get("STOCK_API_BASE", "http://localhost:8003")


def execute(symbol: str) -> str:
    """
    获取股票当前价格

    Args:
        symbol: 股票代码

    Returns:
        格式化的价格信息
    """
    url = f"{STOCK_API_BASE}/stock/price/{symbol}"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        price = data.get("price")
        currency = data.get("currency", "$")

        return f"**{symbol}** 当前价格: {currency}{price:.2f}"

    except Exception as e:
        return f"获取 {symbol} 股价失败: {str(e)}"


if __name__ == "__main__":
    print(execute("AAPL"))

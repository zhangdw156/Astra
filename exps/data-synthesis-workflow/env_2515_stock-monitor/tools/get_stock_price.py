"""
Get Stock Price Tool - 获取单只股票实时价格

使用 Yahoo Finance API 获取股票实时价格，支持A股、港股、美股。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_stock_price",
    "description": "Get real-time stock price for a single stock using Yahoo Finance. "
    "Supports A-shares (600519.SS), HK stocks (0700.HK), and US stocks (AAPL, PDD). "
    "Returns current price, change, and percentage change.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock symbol: A股 (600519.SS), 港股 (0700.HK), 美股 (AAPL, PDD)",
            },
            "name": {"type": "string", "description": "Stock name for display (optional)"},
        },
        "required": ["symbol"],
    },
}

YAHOO_FINANCE_BASE = os.environ.get("YAHOO_FINANCE_BASE", "http://localhost:8003")


def execute(symbol: str, name: str = None) -> str:
    """
    获取股票实时价格

    Args:
        symbol: 股票代码
        name: 股票名称（可选）

    Returns:
        格式化的股票价格信息
    """
    stock_name = name or symbol

    # 优先使用 Mock API（Docker 环境），fallback 到真实 Yahoo Finance
    use_mock = os.environ.get("USE_MOCK", "true").lower() == "true"

    if use_mock:
        return get_stock_price_mock(symbol, stock_name)
    else:
        return get_stock_price_real(symbol, stock_name)


def get_stock_price_mock(symbol: str, stock_name: str) -> str:
    """从 Mock API 获取股票价格"""
    try:
        url = f"{YAHOO_FINANCE_BASE}/quote/{urllib.parse.quote(symbol)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("error"):
            return f"❌ 获取 {stock_name} ({symbol}) 失败: {data['error']}"

        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("changePercent", 0)
        currency = data.get("currency", "$")

        direction = "📈" if change >= 0 else "📉"

        output = f"## {stock_name} ({symbol})\n\n"
        output += f"- **当前价格**: {currency}{price:.2f}\n"
        output += f"- **涨跌**: {direction} {currency}{change:+.2f} ({change_pct:+.2f}%)\n"
        output += f"- **货币**: {currency}\n"

        return output

    except Exception as e:
        return f"❌ 获取 {stock_name} ({symbol}) 失败: {str(e)}"


def get_stock_price_real(symbol: str, stock_name: str) -> str:
    """从真实 Yahoo Finance API 获取股票价格"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return f"❌ 获取 {stock_name} ({symbol}) 失败: 无数据"

        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", price)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        # 判断货币
        if symbol.endswith(".SS"):
            currency = "¥"
        elif symbol.endswith(".HK"):
            currency = "HK$"
        else:
            currency = "$"

        direction = "📈" if change >= 0 else "📉"

        output = f"## {stock_name} ({symbol})\n\n"
        output += f"- **当前价格**: {currency}{price:.2f}\n"
        output += f"- **涨跌**: {direction} {currency}{change:+.2f} ({change_pct:+.2f}%)\n"
        output += f"- **昨收**: {currency}{prev_close:.2f}\n"
        output += f"- **货币**: {currency}\n"

        return output

    except Exception as e:
        return f"❌ 获取 {stock_name} ({symbol}) 失败: {str(e)}"


if __name__ == "__main__":
    print(execute("AAPL", "Apple"))
    print(execute("600519.SS", "贵州茅台"))
    print(execute("0700.HK", "腾讯控股"))

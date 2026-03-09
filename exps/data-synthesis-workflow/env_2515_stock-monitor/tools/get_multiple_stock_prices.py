"""
Get Multiple Stock Prices Tool - 批量获取多只股票价格

同时获取多只股票的价格信息。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_multiple_stock_prices",
    "description": "Get real-time prices for multiple stocks at once. "
    "Useful for monitoring a portfolio of stocks. "
    "Input as a list of stock symbols with optional names.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "stocks": {
                "type": "string",
                "description": "List of stocks in format: 'symbol:name,symbol:name,...' e.g., 'AAPL:Apple,600519.SS:贵州茅台,0700.HK:腾讯控股'",
            }
        },
        "required": ["stocks"],
    },
}

YAHOO_FINANCE_BASE = os.environ.get("YAHOO_FINANCE_BASE", "http://localhost:8003")


def execute(stocks: str) -> str:
    """
    批量获取股票价格

    Args:
        stocks: 股票列表，格式 "symbol:name,symbol:name,..."

    Returns:
        多只股票的价格信息
    """
    use_mock = os.environ.get("USE_MOCK", "true").lower() == "true"

    # 解析股票列表
    stock_list = []
    for item in stocks.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            symbol, name = item.split(":", 1)
            stock_list.append((symbol.strip(), name.strip()))
        else:
            stock_list.append((item.strip(), item.strip()))

    if not stock_list:
        return "❌ 请提供有效的股票列表"

    output = f"## 股票价格监控 ({len(stock_list)} 只)\n\n"

    for symbol, name in stock_list:
        if use_mock:
            result = get_stock_price_mock(symbol, name)
        else:
            result = get_stock_price_real(symbol, name)
        output += result + "\n---\n\n"

    return output


def get_stock_price_mock(symbol: str, stock_name: str) -> str:
    """从 Mock API 获取股票价格"""
    try:
        url = f"{YAHOO_FINANCE_BASE}/quote/{urllib.parse.quote(symbol)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("error"):
            return f"❌ {stock_name} ({symbol}): {data['error']}"

        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("changePercent", 0)
        currency = data.get("currency", "$")

        direction = "📈" if change >= 0 else "📉"

        return (
            f"**{stock_name}** ({symbol})\n{direction} {currency}{price:.2f} ({change_pct:+.2f}%)"
        )

    except Exception as e:
        return f"❌ {stock_name} ({symbol}): {str(e)}"


def get_stock_price_real(symbol: str, stock_name: str) -> str:
    """从真实 Yahoo Finance API 获取股票价格"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return f"❌ {stock_name} ({symbol}): 无数据"

        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", price)
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        if symbol.endswith(".SS"):
            currency = "¥"
        elif symbol.endswith(".HK"):
            currency = "HK$"
        else:
            currency = "$"

        direction = "📈" if change >= 0 else "📉"

        return (
            f"**{stock_name}** ({symbol})\n{direction} {currency}{price:.2f} ({change_pct:+.2f}%)"
        )

    except Exception as e:
        return f"❌ {stock_name} ({symbol}): {str(e)}"


if __name__ == "__main__":
    print(execute("AAPL:Apple,600519.SS:贵州茅台,0700.HK:腾讯控股"))

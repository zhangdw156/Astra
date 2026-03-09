"""
Yahoo Finance API Mock - 模拟 Yahoo Finance 股票价格API

提供实时股票价格数据，用于测试和开发。
"""

import random
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Yahoo Finance Mock API")


MOCK_STOCKS = {
    "600519.SS": {"name": "贵州茅台", "price": 1650.00, "currency": "¥"},
    "0700.HK": {"name": "腾讯控股", "price": 520.00, "currency": "HK$"},
    "PDD": {"name": "拼多多", "price": 125.00, "currency": "$"},
    "AAPL": {"name": "Apple Inc.", "price": 185.00, "currency": "$"},
    "MSFT": {"name": "Microsoft", "price": 420.00, "currency": "$"},
    "GOOGL": {"name": "Alphabet", "price": 175.00, "currency": "$"},
    "AMZN": {"name": "Amazon", "price": 195.00, "currency": "$"},
    "TSLA": {"name": "Tesla", "price": 245.00, "currency": "$"},
    "BABA": {"name": "阿里巴巴", "price": 125.00, "currency": "$"},
    "TCEHY": {"name": "腾讯ADR", "price": 52.00, "currency": "$"},
    "9988.HK": {"name": "阿里巴巴港股", "price": 98.00, "currency": "HK$"},
    "3690.HK": {"name": "美团", "price": 185.00, "currency": "HK$"},
    "1810.HK": {"name": "小米", "price": 28.00, "currency": "HK$"},
}


def get_mock_price(symbol):
    """获取模拟价格，加入随机波动"""
    if symbol in MOCK_STOCKS:
        base_price = MOCK_STOCKS[symbol]["price"]
        variance = random.uniform(-0.02, 0.02)
        return base_price * (1 + variance)
    return None


@app.get("/stock/price/{symbol}")
async def get_stock_price(symbol: str):
    """获取股票价格"""
    price = get_mock_price(symbol)

    if price is None:
        return {"error": "Stock not found", "symbol": symbol}

    stock_info = MOCK_STOCKS.get(symbol, {})
    currency = stock_info.get("$", "$")

    if symbol.endswith(".SS"):
        currency = "¥"
    elif symbol.endswith(".HK"):
        currency = "HK$"

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "currency": currency,
        "name": stock_info.get("name", symbol),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/stock/info/{symbol}")
async def get_stock_info(symbol: str):
    """获取股票信息"""
    if symbol in MOCK_STOCKS:
        stock = MOCK_STOCKS[symbol]
        return {
            "symbol": symbol,
            "name": stock["name"],
            "currency": stock["currency"],
            "price": stock["price"],
        }
    return {"error": "Stock not found", "symbol": symbol}


@app.get("/stock/list")
async def list_stocks():
    """列出所有可用股票"""
    return {"stocks": [{"symbol": s, "name": MOCK_STOCKS[s]["name"]} for s in MOCK_STOCKS]}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)

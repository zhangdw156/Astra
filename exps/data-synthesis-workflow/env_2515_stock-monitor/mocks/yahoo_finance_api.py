"""
Yahoo Finance API Mock - 模拟 Yahoo Finance API

提供预设的股票数据，用于测试和开发。
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
import random
from datetime import datetime

app = FastAPI(title="Yahoo Finance Mock API")


STOCK_DATA = {
    "AAPL": {"name": "Apple Inc.", "price": 185.50, "prev_close": 182.30, "currency": "$"},
    "PDD": {"name": "Pinduoduo Inc.", "price": 125.80, "prev_close": 122.50, "currency": "$"},
    "MSFT": {"name": "Microsoft Corp.", "price": 415.20, "prev_close": 410.80, "currency": "$"},
    "GOOGL": {"name": "Alphabet Inc.", "price": 175.30, "prev_close": 172.90, "currency": "$"},
    "AMZN": {"name": "Amazon.com Inc.", "price": 198.50, "prev_close": 195.20, "currency": "$"},
    "TSLA": {"name": "Tesla Inc.", "price": 245.60, "prev_close": 250.30, "currency": "$"},
    "NVDA": {"name": "NVIDIA Corp.", "price": 875.40, "prev_close": 860.20, "currency": "$"},
    "META": {"name": "Meta Platforms", "price": 525.80, "prev_close": 518.90, "currency": "$"},
    "600519.SS": {"name": "贵州茅台", "price": 1680.00, "prev_close": 1650.00, "currency": "¥"},
    "000001.SS": {"name": "上证指数", "price": 3450.50, "prev_close": 3420.30, "currency": "¥"},
    "0700.HK": {"name": "腾讯控股", "price": 385.60, "prev_close": 380.20, "currency": "HK$"},
    "9988.HK": {"name": "阿里巴巴", "price": 78.50, "prev_close": 77.20, "currency": "HK$"},
    "3690.HK": {"name": "美团", "price": 145.80, "prev_close": 143.50, "currency": "HK$"},
    "TCEHY": {"name": "Tencent Holdings", "price": 48.90, "prev_close": 48.20, "currency": "$"},
    "BABA": {"name": "Alibaba Group", "price": 78.30, "prev_close": 77.50, "currency": "$"},
}


@app.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """获取股票报价"""
    symbol = symbol.upper()

    if symbol not in STOCK_DATA:
        return {"error": f"Symbol {symbol} not found"}

    stock = STOCK_DATA[symbol]
    price = stock["price"]
    prev_close = stock["prev_close"]
    change = price - prev_close
    change_percent = (change / prev_close) * 100

    return {
        "symbol": symbol,
        "name": stock["name"],
        "price": price,
        "prev_close": prev_close,
        "change": change,
        "changePercent": change_percent,
        "currency": stock["currency"],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/chart/{symbol}")
async def get_chart(symbol: str):
    """获取股票图表数据"""
    symbol = symbol.upper()

    if symbol not in STOCK_DATA:
        return {"error": f"Symbol {symbol} not found"}

    stock = STOCK_DATA[symbol]

    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": symbol,
                        "regularMarketPrice": stock["price"],
                        "previousClose": stock["prev_close"],
                        "currency": stock["currency"],
                    }
                }
            ]
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)

"""
Kalshi API Mock - 模拟 Kalshi 预测市场API

Kalshi 是 CFTC 监管的美国预测市场，提供美联储利率、GDP、CPI等经济预测。
"""

from typing import Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

app = FastAPI(title="Kalshi Mock API")


class Market(BaseModel):
    id: str
    title: str
    yes_price: float
    no_price: float
    volume: int
    openInterest: int
    closeDate: Optional[str] = None


# 预置市场数据
MOCK_MARKETS = {
    "fed": [
        Market(
            id="FED-2026-MAR",
            title="Will the Fed cut rates in March 2026?",
            yes_price=0.35,
            no_price=0.65,
            volume=1250000,
            openInterest=450000,
            closeDate="2026-03-31T00:00:00Z"
        ),
        Market(
            id="FED-2026-JUN",
            title="Will the Fed cut rates by June 2026?",
            yes_price=0.55,
            no_price=0.45,
            volume=980000,
            openInterest=320000,
            closeDate="2026-06-30T00:00:00Z"
        ),
        Market(
            id="FED-RATE-50BP",
            title="Will Fed cut by 50bps in Q2 2026?",
            yes_price=0.22,
            no_price=0.78,
            volume=650000,
            openInterest=180000,
            closeDate="2026-06-30T00:00:00Z"
        ),
        Market(
            id="FED-RATE-25BP",
            title="Will Fed cut by 25bps in Q2 2026?",
            yes_price=0.68,
            no_price=0.32,
            volume=890000,
            openInterest=290000,
            closeDate="2026-06-30T00:00:00Z"
        ),
    ],
    "economics": [
        Market(
            id="GDP-Q1-2026",
            title="Will US GDP grow >2% in Q1 2026?",
            yes_price=0.62,
            no_price=0.38,
            volume=450000,
            openInterest=150000,
            closeDate="2026-04-30T00:00:00Z"
        ),
        Market(
            id="CPI-FEB-2026",
            title="Will CPI be <3% in February 2026?",
            yes_price=0.58,
            no_price=0.42,
            volume=380000,
            openInterest=120000,
            closeDate="2026-02-28T00:00:00Z"
        ),
        Market(
            id="CPI-MARCH-2026",
            title="Will CPI be <3% in March 2026?",
            yes_price=0.55,
            no_price=0.45,
            volume=410000,
            openInterest=135000,
            closeDate="2026-03-31T00:00:00Z"
        ),
        Market(
            id="GDP-Q2-2026",
            title="Will US GDP grow >2.5% in Q2 2026?",
            yes_price=0.48,
            no_price=0.52,
            volume=520000,
            openInterest=180000,
            closeDate="2026-07-31T00:00:00Z"
        ),
    ],
    "trending": [
        Market(
            id="BTC-100K",
            title="Will BTC reach $100K by end of 2026?",
            yes_price=0.72,
            no_price=0.28,
            volume=2100000,
            openInterest=850000,
            closeDate="2026-12-31T00:00:00Z"
        ),
        Market(
            id="ETH-5K",
            title="Will ETH reach $5K by end of 2026?",
            yes_price=0.65,
            no_price=0.35,
            volume=1800000,
            openInterest=720000,
            closeDate="2026-12-31T00:00:00Z"
        ),
        Market(
            id="AI-JOBS",
            title="Will AI create more jobs than it displaces in 2026?",
            yes_price=0.58,
            no_price=0.42,
            volume=950000,
            openInterest=320000,
            closeDate="2026-12-31T00:00:00Z"
        ),
    ],
}


@app.get("/markets")
async def get_markets(
    type: str = Query(None, description="Market type: fed, economics"),
    limit: int = Query(10, description="Max results")
):
    """获取市场列表"""
    if type and type in MOCK_MARKETS:
        markets = MOCK_MARKETS[type][:limit]
    else:
        # 返回所有市场
        all_markets = []
        for markets_list in MOCK_MARKETS.values():
            all_markets.extend(markets_list)
        markets = all_markets[:limit]

    return {
        "markets": [m.dict() for m in markets],
        "total": len(markets)
    }


@app.get("/markets/fed")
async def get_fed_markets(limit: int = Query(10)):
    """获取美联储相关市场"""
    markets = MOCK_MARKETS.get("fed", [])[:limit]
    return {"markets": [m.dict() for m in markets], "total": len(markets)}


@app.get("/markets/economics")
async def get_economics_markets(limit: int = Query(10)):
    """获取经济相关市场"""
    markets = MOCK_MARKETS.get("economics", [])[:limit]
    return {"markets": [m.dict() for m in markets], "total": len(markets)}


@app.get("/markets/trending")
async def get_trending_markets(limit: int = Query(10)):
    """获取热门市场"""
    markets = MOCK_MARKETS.get("trending", [])[:limit]
    return {"markets": [m.dict() for m in markets], "total": len(markets)}


@app.get("/markets/search")
async def search_markets(q: str = Query(..., description="Search query"), limit: int = Query(10)):
    """搜索市场"""
    # 简单的模拟搜索
    all_markets = []
    for markets_list in MOCK_MARKETS.values():
        all_markets.extend(markets_list)

    # 模拟搜索匹配
    query_lower = q.lower()
    results = [
        m for m in all_markets
        if query_lower in m.title.lower()
    ][:limit]

    return {"markets": [m.dict() for m in results], "total": len(results)}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

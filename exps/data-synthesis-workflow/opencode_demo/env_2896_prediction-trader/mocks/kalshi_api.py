"""
Kalshi API Mock - 模拟 Kalshi 预测市场 API

从 SQLite 状态后端读取数据，与工具共享同一数据源，保证状态一致（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

from datetime import datetime
import sys
from pathlib import Path

# 允许从 mocks/ 运行时找到项目根
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Query

app = FastAPI(title="Kalshi Mock API")


def _row_to_market(r: dict) -> dict:
    """将 DB 行转为 API 返回格式。"""
    return {
        "id": r["id"],
        "title": r["title"],
        "yes_price": r["yes_price"],
        "no_price": r["no_price"],
        "volume": r["volume"],
        "openInterest": r.get("open_interest", 0),
        "closeDate": r.get("close_date"),
    }


@app.get("/markets")
async def get_markets(
    type: str = Query(None, description="Market type: fed, economics, trending"),
    limit: int = Query(10, description="Max results"),
):
    """获取市场列表：从状态层读取。"""
    from state import read_kalshi_markets

    if type:
        markets = read_kalshi_markets(category=type, limit=limit)
    else:
        markets = read_kalshi_markets(limit=limit)
    return {
        "markets": [_row_to_market(m) for m in markets],
        "total": len(markets),
    }


@app.get("/markets/fed")
async def get_fed_markets(limit: int = Query(10)):
    """获取美联储相关市场。"""
    from state import read_kalshi_markets

    markets = read_kalshi_markets(category="fed", limit=limit)
    return {"markets": [_row_to_market(m) for m in markets], "total": len(markets)}


@app.get("/markets/economics")
async def get_economics_markets(limit: int = Query(10)):
    """获取经济相关市场。"""
    from state import read_kalshi_markets

    markets = read_kalshi_markets(category="economics", limit=limit)
    return {"markets": [_row_to_market(m) for m in markets], "total": len(markets)}


@app.get("/markets/trending")
async def get_trending_markets(limit: int = Query(10)):
    """获取热门市场。"""
    from state import read_kalshi_markets

    markets = read_kalshi_markets(category="trending", limit=limit)
    return {"markets": [_row_to_market(m) for m in markets], "total": len(markets)}


@app.get("/markets/search")
async def search_markets(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10),
):
    """搜索市场：按 title 模糊匹配。"""
    from state import read_kalshi_markets

    markets = read_kalshi_markets(search_query=q, limit=limit)
    return {"markets": [_row_to_market(m) for m in markets], "total": len(markets)}


@app.get("/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

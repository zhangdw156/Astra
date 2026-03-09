"""
Simmer API Mock - 模拟 Simmer API 用于 Polymarket Copytrading

Simmer SDK 提供 copytrading 功能，允许用户镜像成功的 Polymarket 交易员的头寸。
"""

import random
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Query, Header
from pydantic import BaseModel

app = FastAPI(title="Simmer Mock API")


class Position(BaseModel):
    question: str
    shares_yes: float
    shares_no: float
    current_value: float
    pnl: float
    cost_basis: float
    venue: str


MOCK_WALLET_POSITIONS = {
    "0x1234567890abcdef1234567890abcdef12345678": [
        {
            "question": "Will BTC reach $100K by end of 2026?",
            "shares_yes": 45.0,
            "shares_no": 0.0,
            "current_value": 32.40,
            "pnl": 2.40,
            "cost_basis": 30.00,
            "market_id": "btc-100k-2026",
        },
        {
            "question": "Will Fed cut rates in Q2 2026?",
            "shares_yes": 120.0,
            "shares_no": 0.0,
            "current_value": 81.60,
            "pnl": -8.40,
            "cost_basis": 90.00,
            "market_id": "fed-cut-q2-2026",
        },
        {
            "question": "Will Trump win 2026 midterms?",
            "shares_no": 80.0,
            "shares_yes": 0.0,
            "current_value": 56.00,
            "pnl": 16.00,
            "cost_basis": 40.00,
            "market_id": "trump-midterms-2026",
        },
    ],
    "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": [
        {
            "question": "Will BTC reach $100K by end of 2026?",
            "shares_yes": 100.0,
            "shares_no": 0.0,
            "current_value": 72.00,
            "pnl": 22.00,
            "cost_basis": 50.00,
            "market_id": "btc-100k-2026",
        },
        {
            "question": "Will ETH reach $5K by June 2026?",
            "shares_yes": 60.0,
            "shares_no": 0.0,
            "current_value": 34.80,
            "pnl": 4.80,
            "cost_basis": 30.00,
            "market_id": "eth-5k-2026",
        },
    ],
}


MOCK_USER_POSITIONS = [
    {
        "question": "Will BTC reach $100K by end of 2026?",
        "shares_yes": 30.0,
        "shares_no": 0.0,
        "current_value": 21.60,
        "pnl": 1.60,
        "cost_basis": 20.00,
        "venue": "polymarket",
        "market_id": "btc-100k-2026",
    },
    {
        "question": "Will Fed cut rates in Q2 2026?",
        "shares_yes": 50.0,
        "shares_no": 0.0,
        "current_value": 34.00,
        "pnl": -6.00,
        "cost_basis": 40.00,
        "venue": "polymarket",
        "market_id": "fed-cut-q2-2026",
    },
]


def verify_auth(authorization: str) -> bool:
    """验证 API Key"""
    if not authorization or "Bearer" not in authorization:
        return False
    return True


@app.get("/api/sdk/portfolio")
async def get_portfolio(venue: str = Query("polymarket"), authorization: str = Header(None)):
    """获取投资组合余额"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    if venue == "simmer":
        return {
            "balance": 10000.00,
            "available": 10000.00,
            "positions_value": 0.00,
            "venue": "simmer",
        }
    else:
        return {
            "balance": 250.00,
            "available": 180.50,
            "positions_value": 55.60,
            "venue": "polymarket",
        }


@app.get("/api/sdk/positions")
async def get_positions(venue: str = Query("polymarket"), authorization: str = Header(None)):
    """获取用户头寸"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    filtered = [p for p in MOCK_USER_POSITIONS if p.get("venue") == venue]
    return {"positions": filtered, "total": len(filtered)}


@app.get("/api/sdk/wallet/positions")
async def get_wallet_positions(
    wallet: str = Query(...), limit: int = Query(20), authorization: str = Header(None)
):
    """获取指定钱包的头寸"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    positions = MOCK_WALLET_POSITIONS.get(wallet.lower(), [])[:limit]
    return {"positions": positions, "total": len(positions)}


@app.post("/api/sdk/copytrading/execute")
async def execute_copytrading(request: dict, authorization: str = Header(None)):
    """执行 copytrading"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    wallets = request.get("wallets", [])
    dry_run = request.get("dry_run", True)
    buy_only = request.get("buy_only", True)
    max_usd = request.get("max_usd_per_position", 50)

    wallets_analyzed = len(wallets)
    positions_found = 0
    for w in wallets:
        positions_found += len(MOCK_WALLET_POSITIONS.get(w.lower(), []))

    conflicts_skipped = 2
    top_n_used = min(positions_found, 10) if positions_found else 0

    trades = []
    if positions_found > 0:
        trade_count = min(random.randint(2, 5), request.get("max_trades", 10))
        for i in range(trade_count):
            market_titles = [
                "Will BTC reach $100K by end of 2026?",
                "Will Fed cut rates in Q2 2026?",
                "Will Trump win 2026 midterms?",
                "Will ETH reach $5K by June 2026?",
            ]
            trades.append(
                {
                    "action": "buy",
                    "side": random.choice(["yes", "no"]),
                    "shares": random.uniform(10, 50),
                    "estimated_price": round(random.uniform(0.1, 0.9), 3),
                    "estimated_cost": round(random.uniform(5, max_usd), 2),
                    "market_title": market_titles[i % len(market_titles)],
                    "success": not dry_run,
                    "trade_id": f"trade-{random.randint(1000, 9999)}" if not dry_run else None,
                }
            )

    return {
        "success": True,
        "wallets_analyzed": wallets_analyzed,
        "positions_found": positions_found,
        "conflicts_skipped": conflicts_skipped,
        "top_n_used": top_n_used,
        "whale_exits_detected": 0,
        "trades": trades,
        "trades_needed": len(trades),
        "trades_executed": 0 if dry_run else len(trades),
        "summary": "Dry run complete - no trades executed"
        if dry_run
        else f"Executed {len(trades)} trades successfully",
    }


@app.post("/api/sdk/copytrading/whale-exits")
async def check_whale_exits(request: dict, authorization: str = Header(None)):
    """检查鲸鱼平仓"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    wallets = request.get("wallets", [])
    dry_run = request.get("dry_run", True)

    whale_exits_detected = 0
    trades = []

    if random.random() < 0.3:
        whale_exits_detected = random.randint(1, 3)
        for i in range(whale_exits_detected):
            trades.append(
                {
                    "action": "sell",
                    "side": random.choice(["yes", "no"]),
                    "shares": random.uniform(10, 30),
                    "estimated_price": round(random.uniform(0.1, 0.9), 3),
                    "estimated_cost": round(random.uniform(5, 25), 2),
                    "market_title": f"Market {i + 1}",
                    "success": not dry_run,
                }
            )

    return {
        "success": True,
        "whale_exits_detected": whale_exits_detected,
        "trades": trades,
        "summary": f"Found {whale_exits_detected} positions to close"
        if whale_exits_detected
        else "No exits detected",
    }


@app.get("/api/sdk/copytrading/config")
async def get_copytrading_config(authorization: str = Header(None)):
    """获取 copytrading 配置"""
    if not verify_auth(authorization):
        return {"error": "Unauthorized", "status_code": 401}

    return {
        "wallets": [
            "0x1234567890abcdef1234567890abcdef12345678",
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ],
        "top_n": None,
        "max_usd": 50,
        "max_trades": 10,
        "venue": "polymarket",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

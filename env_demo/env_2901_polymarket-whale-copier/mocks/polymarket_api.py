"""
Polymarket API Mock - 模拟 Polymarket 预测市场API

Polymarket 是基于 Polygon 的离岸预测市场，提供加密货币、政治、体育等预测。
"""

from typing import Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

app = FastAPI(title="Polymarket Mock API")


class Transaction(BaseModel):
    id: str
    wallet_address: str
    market_id: str
    market_question: str
    side: str
    amount: int
    price: float
    total: float
    timestamp: str


class Position(BaseModel):
    market_id: str
    market_question: str
    side: str
    shares: int
    entry_price: float
    current_price: float
    pnl: float


class Market(BaseModel):
    id: str
    question: str
    yes_price: float
    no_price: float
    volume: int
    open_interest: int
    end_date: Optional[str] = None
    description: Optional[str] = None
    group_item_title: Optional[str] = None
    outcome_type: Optional[str] = None


class Trader(BaseModel):
    address: str
    name: str
    profit: float
    win_rate: float
    total_trades: int
    volume: float


MOCK_WALLETS = {
    "0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f": [
        Transaction(
            id="tx001",
            wallet_address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f",
            market_id="m1",
            market_question="Will BTC reach $100K by end of 2026?",
            side="buy",
            amount=500,
            price=0.35,
            total=175.0,
            timestamp="2026-03-08T10:30:00Z",
        ),
        Transaction(
            id="tx002",
            wallet_address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f",
            market_id="m2",
            market_question="Will Fed cut rates in Q2 2026?",
            side="buy",
            amount=1000,
            price=0.55,
            total=550.0,
            timestamp="2026-03-07T15:45:00Z",
        ),
    ],
    "0xa1b2c3d4e5f6789012345678901234567890abcd": [
        Transaction(
            id="tx003",
            wallet_address="0xa1b2c3d4e5f6789012345678901234567890abcd",
            market_id="m3",
            market_question="Will ETH reach $5K by end of 2026?",
            side="buy",
            amount=200,
            price=0.65,
            total=130.0,
            timestamp="2026-03-08T09:00:00Z",
        ),
    ],
}

MOCK_POSITIONS = {
    "0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f": [
        Position(
            market_id="m1",
            market_question="Will BTC reach $100K by end of 2026?",
            side="buy",
            shares=500,
            entry_price=0.35,
            current_price=0.72,
            pnl=185.0,
        ),
        Position(
            market_id="m2",
            market_question="Will Fed cut rates in Q2 2026?",
            side="buy",
            shares=1000,
            entry_price=0.55,
            current_price=0.68,
            pnl=130.0,
        ),
    ]
}

MOCK_MARKETS = [
    Market(
        id="m1",
        question="Will BTC reach $100K by end of 2026?",
        yes_price=0.72,
        no_price=0.28,
        volume=2100000,
        open_interest=850000,
        end_date="2026-12-31T00:00:00Z",
        group_item_title="Crypto",
        outcome_type="binary",
    ),
    Market(
        id="m2",
        question="Will Fed cut rates in Q2 2026?",
        yes_price=0.68,
        no_price=0.32,
        volume=890000,
        open_interest=290000,
        end_date="2026-06-30T00:00:00Z",
        group_item_title="Economics",
        outcome_type="binary",
    ),
    Market(
        id="m3",
        question="Will ETH reach $5K by end of 2026?",
        yes_price=0.65,
        no_price=0.35,
        volume=1800000,
        open_interest=720000,
        end_date="2026-12-31T00:00:00Z",
        group_item_title="Crypto",
        outcome_type="binary",
    ),
    Market(
        id="m4",
        question="Will AI create more jobs than it displaces in 2026?",
        yes_price=0.58,
        no_price=0.42,
        volume=950000,
        open_interest=320000,
        end_date="2026-12-31T00:00:00Z",
        group_item_title="Technology",
        outcome_type="binary",
    ),
    Market(
        id="m5",
        question="Will there be a major crypto regulation in US by Q3 2026?",
        yes_price=0.45,
        no_price=0.55,
        volume=650000,
        open_interest=180000,
        end_date="2026-09-30T00:00:00Z",
        group_item_title="Crypto",
        outcome_type="binary",
    ),
]

MOCK_WHALES = [
    Trader(
        address="0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f",
        name="CryptoKing",
        profit=125000.0,
        win_rate=0.68,
        total_trades=342,
        volume=2500000.0,
    ),
    Trader(
        address="0xa1b2c3d4e5f6789012345678901234567890abcd",
        name="AlphaWhale",
        profit=89000.0,
        win_rate=0.72,
        total_trades=215,
        volume=1800000.0,
    ),
    Trader(
        address="0xdef01234567890abcdef012345678901234567cd",
        name="PolymarketPro",
        profit=67000.0,
        win_rate=0.65,
        total_trades=189,
        volume=1200000.0,
    ),
]


@app.get("/markets/trending")
async def get_trending_markets(limit: int = Query(10)):
    """获取热门市场"""
    markets = MOCK_MARKETS[:limit]
    return {"markets": [m.dict() for m in markets]}


@app.get("/markets/{market_id}")
async def get_market(market_id: str):
    """获取特定市场详情"""
    for market in MOCK_MARKETS:
        if market.id == market_id:
            return {"market": market.dict()}
    return {"error": "Market not found"}, 404


@app.get("/wallet/{wallet_address}/transactions")
async def get_wallet_transactions(wallet_address: str, limit: int = Query(20)):
    """获取钱包交易历史"""
    txs = MOCK_WALLETS.get(wallet_address.lower(), [])
    return {"transactions": [t.dict() for t in txs[:limit]]}


@app.get("/wallet/{wallet_address}/transactions/{tx_id}")
async def get_transaction(wallet_address: str, tx_id: str):
    """获取特定交易详情"""
    txs = MOCK_WALLETS.get(wallet_address.lower(), [])
    for tx in txs:
        if tx.id == tx_id:
            return {"transaction": tx.dict()}
    return {"error": "Transaction not found"}, 404


@app.get("/wallet/{wallet_address}/positions")
async def get_wallet_positions(wallet_address: str):
    """获取钱包当前持仓"""
    positions = MOCK_POSITIONS.get(wallet_address.lower(), [])
    return {"positions": [p.dict() for p in positions]}


@app.get("/leaderboard")
async def get_leaderboard(limit: int = Query(10)):
    """获取排行榜"""
    traders = MOCK_WHALES[:limit]
    return {"traders": [t.dict() for t in traders]}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

"""
Data API Mock - Mock Polymarket Data API

Simulates the Data API for user positions, trades, and P&L.
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime
import random

app = FastAPI(title="Polymarket Data Mock API")


class Position(BaseModel):
    title: str
    outcome: str
    size: float
    avgPrice: float
    curPrice: float
    pnl: float


MOCK_POSITIONS = {
    "0x7845bc5e15bc9c41be5ac0725e68a16ec02b51b5": [
        {
            "title": "Will Bitcoin reach $150K by end of 2026?",
            "outcome": "Yes",
            "size": 150.5,
            "avgPrice": 0.42,
            "curPrice": 0.45,
            "pnl": 4.52,
        },
        {
            "title": "Will Trump win 2026 midterms?",
            "outcome": "Yes",
            "size": 200.0,
            "avgPrice": 0.48,
            "curPrice": 0.52,
            "pnl": 8.0,
        },
        {
            "title": "Will there be a Fed rate cut in Q2 2026?",
            "outcome": "No",
            "size": 100.0,
            "avgPrice": 0.35,
            "curPrice": 0.32,
            "pnl": -3.0,
        },
    ],
    "0x1234567890abcdef1234567890abcdef12345678": [
        {
            "title": "Will BTC reach $100K by end of 2026?",
            "outcome": "Yes",
            "size": 500.0,
            "avgPrice": 0.65,
            "curPrice": 0.72,
            "pnl": 35.0,
        }
    ],
}

MOCK_TRADES = [
    {"side": "BUY", "size": 150.5, "price": 0.42, "timestamp": "2026-01-15T10:30:00Z"},
    {"side": "BUY", "size": 200.0, "price": 0.48, "timestamp": "2026-01-20T14:22:00Z"},
    {"side": "BUY", "size": 100.0, "price": 0.35, "timestamp": "2026-02-01T09:15:00Z"},
    {"side": "SELL", "size": 50.0, "price": 0.55, "timestamp": "2026-02-10T16:45:00Z"},
]

MOCK_PNL = [
    {"date": "2026-01", "pnl": 12.52},
    {"date": "2026-02", "pnl": -3.00},
    {"date": "2026-03", "pnl": 45.20},
]


@app.get("/positions")
async def get_positions(user: str = Query(...)):
    """Get user positions."""
    wallet = user.lower()
    return MOCK_POSITIONS.get(wallet, [])


@app.get("/trades")
async def get_trades(user: str = Query(...)):
    """Get user trade history."""
    wallet = user.lower()
    if wallet in MOCK_POSITIONS:
        return MOCK_TRADES
    return []


@app.get("/profit-loss")
async def get_profit_loss(user: str = Query(...)):
    """Get user P&L history."""
    wallet = user.lower()
    if wallet in MOCK_POSITIONS:
        return MOCK_PNL
    return []


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)

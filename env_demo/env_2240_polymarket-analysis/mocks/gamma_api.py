"""
Gamma API Mock - Mock Polymarket Gamma API

Simulates the Gamma API for market data, prices, and search.
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Polymarket Gamma Mock API")


class Market(BaseModel):
    id: str
    question: str
    slug: str
    outcomePrices: list
    volume: float
    liquidity: float
    endDate: str | None = None
    active: bool = True
    closed: bool = False


MOCK_MARKETS = [
    {
        "id": "1068346",
        "question": "Will Bitcoin reach $150K by end of 2026?",
        "slug": "bitcoin-150k-2026",
        "outcomePrices": ["0.45", "0.55"],
        "volume": 4200000,
        "liquidity": 2100000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068347",
        "question": "Will Trump win 2026 midterms?",
        "slug": "trump-win-2026-midterms",
        "outcomePrices": ["0.52", "0.48"],
        "volume": 8100000,
        "liquidity": 4500000,
        "endDate": "2026-11-03T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068348",
        "question": "Will there be a Fed rate cut in Q2 2026?",
        "slug": "fed-rate-cut-q2-2026",
        "outcomePrices": ["0.68", "0.32"],
        "volume": 5400000,
        "liquidity": 2800000,
        "endDate": "2026-06-30T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068349",
        "question": "Will ETH reach $5K by June 2026?",
        "slug": "eth-5k-june-2026",
        "outcomePrices": ["0.58", "0.42"],
        "volume": 3200000,
        "liquidity": 1800000,
        "endDate": "2026-06-30T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068350",
        "question": "Will AI create more jobs than it displaces in 2026?",
        "slug": "ai-jobs-2026",
        "outcomePrices": ["0.58", "0.42"],
        "volume": 950000,
        "liquidity": 520000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068351",
        "question": "Will Apple release AR glasses in 2026?",
        "slug": "apple-ar-glasses-2026",
        "outcomePrices": ["0.35", "0.65"],
        "volume": 1900000,
        "liquidity": 950000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068352",
        "question": "Will BTC reach $100K by end of 2026?",
        "slug": "btc-100k-2026",
        "outcomePrices": ["0.72", "0.28"],
        "volume": 12500000,
        "liquidity": 6800000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068353",
        "question": "Fed cuts rates by 50bps in 2026?",
        "slug": "fed-cut-50bps-2026",
        "outcomePrices": ["0.35", "0.65"],
        "volume": 3200000,
        "liquidity": 1600000,
        "endDate": "2026-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068354",
        "question": "Will Ethereum flip Bitcoin market cap by 2027?",
        "slug": "eth-flip-btc-2027",
        "outcomePrices": ["0.18", "0.82"],
        "volume": 2800000,
        "liquidity": 1400000,
        "endDate": "2027-12-31T00:00:00Z",
        "active": True,
        "closed": False,
    },
    {
        "id": "1068355",
        "question": "Will Solana reach $500 by June 2026?",
        "slug": "solana-500-june-2026",
        "outcomePrices": ["0.45", "0.55"],
        "volume": 3800000,
        "liquidity": 2100000,
        "endDate": "2026-06-30T00:00:00Z",
        "active": True,
        "closed": False,
    },
]


@app.get("/markets")
async def get_markets(
    slug: str = Query(None),
    active: bool = Query(None),
    closed: bool = Query(None),
    limit: int = Query(100),
):
    """Get markets with optional filters."""
    results = MOCK_MARKETS.copy()

    if slug:
        results = [m for m in results if slug in m["slug"]]
    if active is not None:
        results = [m for m in results if m["active"] == active]
    if closed is not None:
        results = [m for m in results if m["closed"] == closed]

    return results[:limit]


@app.get("/markets/{market_id}")
async def get_market(market_id: str):
    """Get a specific market by ID."""
    for m in MOCK_MARKETS:
        if m["id"] == market_id:
            return m
    return {"error": "Market not found"}, 404


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

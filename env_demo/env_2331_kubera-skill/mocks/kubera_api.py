"""
Kubera API Mock - 模拟 Kubera 投资组合API

Kubera 是一个投资组合追踪平台，提供净资产、资产、债务、配置等功能。
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, Header, HTTPException
from pydantic import BaseModel
import hmac
import hashlib
import time
import json

app = FastAPI(title="Kubera Mock API")

MOCK_API_KEY = "mock-api-key"
MOCK_SECRET = "mock-secret"


class Asset(BaseModel):
    id: str
    name: str
    value: Dict[str, Any]
    cost: Optional[Dict[str, Any]] = None
    ticker: Optional[str] = None
    quantity: Optional[float] = None
    sheetName: Optional[str] = None
    sectionName: Optional[str] = None
    subType: Optional[str] = None


class Debt(BaseModel):
    id: str
    name: str
    value: Dict[str, Any]


class Portfolio(BaseModel):
    id: str
    name: str
    currency: str = "USD"


MOCK_PORTFOLIOS = [
    Portfolio(id="portfolio-001", name="Main Portfolio", currency="USD"),
]

MOCK_ASSETS = [
    Asset(
        id="asset-btc-001",
        name="Bitcoin",
        value={"amount": 50000.00, "currency": "USD"},
        cost={"amount": 35000.00, "currency": "USD"},
        ticker="BTC",
        quantity=0.5,
        sheetName="Crypto",
        sectionName="Cryptocurrencies",
        subType="Cryptocurrency",
    ),
    Asset(
        id="asset-eth-001",
        name="Ethereum",
        value={"amount": 25000.00, "currency": "USD"},
        cost={"amount": 18000.00, "currency": "USD"},
        ticker="ETH",
        quantity=5.0,
        sheetName="Crypto",
        sectionName="Cryptocurrencies",
        subType="Cryptocurrency",
    ),
    Asset(
        id="asset-aapl-001",
        name="Apple Inc.",
        value={"amount": 35000.00, "currency": "USD"},
        cost={"amount": 25000.00, "currency": "USD"},
        ticker="AAPL",
        quantity=200.0,
        sheetName="Equities",
        sectionName="US Stocks",
        subType="Stock",
    ),
    Asset(
        id="asset-googl-001",
        name="Google (Alphabet) Inc.",
        value={"amount": 20000.00, "currency": "USD"},
        cost={"amount": 15000.00, "currency": "USD"},
        ticker="GOOGL",
        quantity=100.0,
        sheetName="Equities",
        sectionName="US Stocks",
        subType="Stock",
    ),
    Asset(
        id="asset-tsla-001",
        name="Tesla Inc.",
        value={"amount": 15000.00, "currency": "USD"},
        cost={"amount": 20000.00, "currency": "USD"},
        ticker="TSLA",
        quantity=50.0,
        sheetName="Equities",
        sectionName="US Stocks",
        subType="Stock",
    ),
    Asset(
        id="asset-house-001",
        name="Primary Residence",
        value={"amount": 500000.00, "currency": "USD"},
        cost={"amount": 400000.00, "currency": "USD"},
        sheetName="Real Estate",
        sectionName="Primary Residence",
        subType="Real Estate",
    ),
    Asset(
        id="asset-cash-001",
        name="Chase Checking",
        value={"amount": 25000.00, "currency": "USD"},
        sheetName="Cash",
        sectionName="Bank Accounts",
        subType="Cash",
    ),
    Asset(
        id="asset-401k-001",
        name="Fidelity 401k",
        value={"amount": 150000.00, "currency": "USD"},
        cost={"amount": 100000.00, "currency": "USD"},
        sheetName="Retirement",
        sectionName="401k",
        subType="Retirement Account",
    ),
    Asset(
        id="asset-roth-001",
        name="Vanguard Roth IRA",
        value={"amount": 75000.00, "currency": "USD"},
        cost={"amount": 50000.00, "currency": "USD"},
        sheetName="Retirement",
        sectionName="Roth IRA",
        subType="Retirement Account",
    ),
    Asset(
        id="asset-shop-001",
        name="Shopify Inc.",
        value={"amount": 10000.00, "currency": "USD"},
        cost={"amount": 8000.00, "currency": "USD"},
        ticker="SHOP",
        quantity=50.0,
        sheetName="Equities",
        sectionName="US Stocks",
        subType="Stock",
    ),
]

MOCK_DEBTS = [
    Debt(
        id="debt-mortgage-001",
        name="Primary Mortgage",
        value={"amount": 350000.00, "currency": "USD"},
    ),
    Debt(id="debt-car-001", name="Auto Loan", value={"amount": 25000.00, "currency": "USD"}),
]


def verify_auth(
    api_token: str, timestamp: str, signature: str, method: str, path: str, body: str = ""
):
    """Verify HMAC-SHA256 signature"""
    if api_token != MOCK_API_KEY:
        return False
    try:
        int(timestamp)
    except ValueError:
        return False
    data = f"{api_token}{timestamp}{method}{path}{body}"
    expected_sig = hmac.new(MOCK_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_sig)


@app.get("/api/v3/data/portfolio")
async def list_portfolios(
    x_api_token: str = Header(...), x_timestamp: str = Header(...), x_signature: str = Header(...)
):
    """List all portfolios"""
    if not verify_auth(x_api_token, x_timestamp, x_signature, "GET", "/api/v3/data/portfolio"):
        raise HTTPException(status_code=401, detail="Authentication failed")

    return {"data": [p.model_dump() for p in MOCK_PORTFOLIOS], "errorCode": 0}


@app.get("/api/v3/data/portfolio/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    x_api_token: str = Header(...),
    x_timestamp: str = Header(...),
    x_signature: str = Header(...),
):
    """Get full portfolio data"""
    path = f"/api/v3/data/portfolio/{portfolio_id}"
    if not verify_auth(x_api_token, x_timestamp, x_signature, "GET", path):
        raise HTTPException(status_code=401, detail="Authentication failed")

    asset_total = sum(a["value"]["amount"] for a in MOCK_ASSETS)
    debt_total = sum(d["value"]["amount"] for d in MOCK_DEBTS)
    net_worth = asset_total - debt_total
    cost_basis = sum(a.get("cost", {}).get("amount", 0) for a in MOCK_ASSETS)
    unrealized_gain = asset_total - cost_basis

    allocation = {}
    for a in MOCK_ASSETS:
        sheet = a.get("sheetName", "Other")
        allocation[sheet] = (
            allocation.get(sheet, 0) + (a["value"]["amount"] / asset_total * 100)
            if asset_total > 0
            else 0
        )

    return {
        "data": {
            "id": portfolio_id,
            "name": "Main Portfolio",
            "ticker": "USD",
            "netWorth": net_worth,
            "assetTotal": asset_total,
            "debtTotal": debt_total,
            "costBasis": cost_basis,
            "unrealizedGain": unrealized_gain,
            "allocationByAssetClass": allocation,
            "asset": [a.model_dump() for a in MOCK_ASSETS],
            "debt": [d.model_dump() for d in MOCK_DEBTS],
            "insurance": [],
            "document": [],
        },
        "errorCode": 0,
    }


@app.post("/api/v3/data/item/{item_id}")
async def update_item(
    item_id: str,
    x_api_token: str = Header(...),
    x_timestamp: str = Header(...),
    x_signature: str = Header(...),
    body: dict = {},
):
    """Update an asset or debt"""
    path = f"/api/v3/data/item/{item_id}"
    body_str = json.dumps(body, separators=(",", ":"))
    if not verify_auth(x_api_token, x_timestamp, x_signature, "POST", path, body_str):
        raise HTTPException(status_code=401, detail="Authentication failed")

    return {"data": {"id": item_id, "updated": True, "changes": body}, "errorCode": 0}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)

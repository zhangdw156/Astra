"""
Portfolio API Mock - 模拟投资组合分析API

模拟加密货币钱包投资组合分析服务，包括多链支持、风险评估、压力测试等。
"""

import random
from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Portfolio Risk Analyzer Mock API")


class AnalyzeRequest(BaseModel):
    wallet: str
    payment_tx: str = None
    chain: str = "all"


MOCK_WALLETS = {
    "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb": {
        "totalValue": 125000,
        "riskScore": 65,
        "breakdown": {
            "stablecoins": 15000,
            "bluechips": 50000,
            "defi": 30000,
            "memecoins": 25000,
            "nfts": 5000,
        },
        "exposures": {"ethereum": 45, "uniswap": 20, "shib": 15, "usdc": 12, "eth": 8},
        "risks": {"concentration": 65, "volatility": 70, "liquidation": 20, "protocol": 30},
        "recommendations": [
            "Reduce memecoin exposure from 20% to 10%",
            "Add 15% stablecoin buffer",
            "Diversify: SHIB is 15% of portfolio",
        ],
    }
}

TOTAL_REVENUE = 5420.0
TOTAL_BANKR_BOUGHT = 677500


def generate_portfolio_data(wallet: str) -> dict:
    """为指定钱包生成模拟数据"""
    if wallet in MOCK_WALLETS:
        return MOCK_WALLETS[wallet]

    random.seed(hash(wallet) % 10000)
    total = random.randint(10000, 500000)
    return {
        "wallet": wallet,
        "totalValue": total,
        "riskScore": random.randint(20, 90),
        "breakdown": {
            "stablecoins": int(total * random.uniform(0.05, 0.3)),
            "bluechips": int(total * random.uniform(0.2, 0.5)),
            "defi": int(total * random.uniform(0.1, 0.3)),
            "memecoins": int(total * random.uniform(0, 0.25)),
            "nfts": int(total * random.uniform(0, 0.1)),
        },
        "exposures": {
            "ethereum": random.randint(20, 60),
            "bitcoin": random.randint(10, 30),
            "usdc": random.randint(5, 20),
            "aave": random.randint(5, 15),
            "uniswap": random.randint(5, 15),
        },
        "risks": {
            "concentration": random.randint(20, 80),
            "volatility": random.randint(30, 90),
            "liquidation": random.randint(0, 50),
            "protocol": random.randint(20, 60),
        },
        "recommendations": [
            f"Reduce {random.choice(['memecoins', 'concentration'])} exposure",
            "Add stablecoin buffer",
            "Consider hedging strategies",
        ],
    }


@app.get("/api/analyze")
async def analyze_portfolio(
    wallet: str = Query(..., description="Wallet address"),
    chain: str = Query("all", description="Chain to analyze"),
):
    """分析钱包投资组合"""
    data = generate_portfolio_data(wallet)
    data["timestamp"] = datetime.now().isoformat()
    return data


@app.get("/api/risk-breakdown")
async def get_risk_breakdown(wallet: str = Query(...)):
    """获取详细风险分解"""
    random.seed(hash(wallet) % 10000)

    return {
        "wallet": wallet,
        "assetClassExposure": {
            "stablecoins": random.randint(5, 25),
            "bluechips": random.randint(20, 50),
            "defi": random.randint(10, 30),
            "memecoins": random.randint(0, 30),
            "nfts": random.randint(0, 15),
        },
        "protocolRisk": {
            "aave": {
                "score": random.randint(10, 40),
                "audited": True,
                "tvl": random.randint(1, 20) * 1e9,
                "age": "2 years",
            },
            "uniswap": {
                "score": random.randint(10, 40),
                "audited": True,
                "tvl": random.randint(2, 10) * 1e9,
                "age": "4 years",
            },
            "compound": {
                "score": random.randint(15, 45),
                "audited": True,
                "tvl": random.randint(1, 5) * 1e9,
                "age": "6 years",
            },
            "some-defi": {
                "score": random.randint(40, 80),
                "audited": False,
                "tvl": random.randint(1, 50) * 1e6,
                "age": "3 months",
            },
        },
        "concentrationRisk": {
            "top5Percent": random.randint(40, 90),
            "diversificationScore": random.randint(20, 80),
            "largestPosition": random.randint(20, 60),
        },
        "impermanentLoss": [
            {"pool": "USDC-ETH", "ilPercent": random.uniform(-5, 15)},
            {"pool": "USDC-USDT", "ilPercent": random.uniform(-1, 2)},
        ],
    }


@app.get("/api/stress-test")
async def stress_test(
    wallet: str = Query(...), scenario: str = Query("crash"), drop: int = Query(50)
):
    """运行压力测试"""
    random.seed(hash(wallet) % 10000)
    data = generate_portfolio_data(wallet)
    total = data["totalValue"]

    if scenario == "crash":
        loss_amount = total * (drop / 100)
        return {
            "wallet": wallet,
            "scenario": "crash",
            "drop": drop,
            "crashImpact": {
                "valueAfterCrash": total - loss_amount,
                "lossAmount": loss_amount,
                "lossPercent": drop,
                "recoveryPrice": 100 + random.randint(20, 100),
                "assetImpact": [
                    {
                        "asset": "ETH",
                        "value": total * 0.4,
                        "newValue": total * 0.4 * (1 - drop / 100),
                    },
                    {
                        "asset": "BTC",
                        "value": total * 0.2,
                        "newValue": total * 0.2 * (1 - drop / 100),
                    },
                    {
                        "asset": "Memecoins",
                        "value": total * 0.2,
                        "newValue": total * 0.2 * (1 - drop * 1.5 / 100),
                    },
                ],
            },
            "correlationAnalysis": [
                {"asset1": "ETH", "asset2": "BTC", "correlation": 0.85},
                {"asset1": "ETH", "asset2": "Alts", "correlation": 0.72},
                {"asset1": "BTC", "asset2": "Gold", "correlation": 0.45},
            ],
            "recommendations": [
                "Consider reducing exposure to high-beta assets",
                "Add stablecoin allocation for defensive positioning",
                "Look into put options for downside protection",
            ],
        }

    elif scenario == "liquidation":
        collateral_ratio = random.uniform(1.2, 3.0)
        liq_price = random.uniform(0.6, 0.9)
        return {
            "wallet": wallet,
            "scenario": "liquidation",
            "liquidationRisk": {
                "collateralRatio": collateral_ratio * 100,
                "liquidationPrice": data["totalValue"] * liq_price,
                "distanceToLiquidation": random.uniform(10, 50),
                "riskScore": random.randint(20, 80),
                "positionsAtRisk": [
                    {"protocol": "Aave", "asset": "USDC", "risk": "Low"},
                    {
                        "protocol": "Compound",
                        "asset": "ETH",
                        "risk": "Medium" if collateral_ratio < 1.5 else "Low",
                    },
                ],
            },
            "recommendations": [
                "Increase collateral ratio above 150%",
                "Consider closing some leveraged positions",
            ],
        }

    elif scenario == "gas":
        return {
            "wallet": wallet,
            "scenario": "gas",
            "gasImpact": {
                "currentGas": random.uniform(5, 20),
                "highGas": random.uniform(50, 200),
                "exitCostCurrent": random.uniform(20, 100),
                "exitCostHigh": random.uniform(200, 800),
                "exitCostPercent": random.uniform(0.1, 2.0),
            },
            "recommendations": [
                "Budget for high-gas scenarios",
                "Consider Layer 2 for future positions",
            ],
        }


@app.get("/api/optimize")
async def get_optimization(wallet: str = Query(...), focus: str = Query("all")):
    """获取优化建议"""
    random.seed(hash(wallet) % 10000)

    return {
        "wallet": wallet,
        "focus": focus,
        "rebalancing": [
            "Reduce memecoins from 20% to 10%",
            "Add 15% to stablecoins",
            "Rebalance ETH allocation to 30%",
        ],
        "hedging": [
            "Consider 5% short position on BTC",
            "Use put options for downside protection",
            "Diversify across more protocols",
        ],
        "yieldOptimization": [
            "Move USDC to Aave (5.2% APY)",
            "Stake ETH for additional yield",
            "Considerstables yield aggregators",
        ],
        "taxLossHarvesting": [
            {"asset": "SHIB", "loss": 2500, "replacement": "LOVE"},
            {"asset": "PEPE", "loss": 1200, "replacement": "WIF"},
        ],
        "expectedImpact": {
            "riskReduction": random.randint(10, 30),
            "yieldImprovement": random.uniform(1, 4),
            "taxSavings": random.randint(500, 2000),
        },
    }


@app.get("/api/payment/verify")
async def verify_payment(wallet: str = Query(...), tx_hash: str = Query(None)):
    """验证支付或$BANKR持有"""
    random.seed(hash(wallet) % 10000)

    bankr_balance = random.randint(0, 5000)
    has_payment = tx_hash is not None

    return {
        "hasAccess": bankr_balance >= 1000 or has_payment,
        "bankrBalance": bankr_balance,
        "payment": {"amount": 5.0, "timestamp": "2026-01-15T10:30:00Z", "valid": True}
        if has_payment
        else None,
        "subscription": {
            "status": "active" if random.random() > 0.5 else "none",
            "expires": "2026-02-15T00:00:00Z",
        },
    }


@app.get("/api/buyback/execute")
async def execute_buyback(amount: float = Query(...), admin_key: str = Query(...)):
    """执行回购"""
    global TOTAL_REVENUE, TOTAL_BANKR_BOUGHT

    if admin_key != "secret":
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Invalid admin key")

    bankr_bought = amount / 0.008
    price = 0.008

    TOTAL_REVENUE += amount
    TOTAL_BANKR_BOUGHT += bankr_bought

    return {
        "success": True,
        "amountUsdc": amount,
        "bankrBought": bankr_bought,
        "price": price,
        "txHash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
        "stats": {
            "totalRevenue": TOTAL_REVENUE,
            "totalBankrBought": TOTAL_BANKR_BOUGHT,
            "avgPrice": 0.008,
            "buyPressure": TOTAL_REVENUE,
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

"""
UnifAI/Polymarket API Mock - 模拟 UnifAI Agent API 用于 Polymarket 数据

Polymarket 是一个基于 Polygon 的离岸预测市场，提供加密货币、政治、体育等预测。

注意：这是 Agentic API，返回的是 AI 生成的文本分析，而非结构化数据。
"""

from typing import Optional
from fastapi import FastAPI, Query, Header
from pydantic import BaseModel
import random
from datetime import datetime

app = FastAPI(title="UnifAI Mock API")


class AgentRequest(BaseModel):
    query: str
    tools: Optional[list] = None


class AgentResponse(BaseModel):
    response: str
    tools_used: Optional[list] = None
    data: Optional[dict] = None


# 预置的 Polymarket 数据
MOCK_POLYMARKET_DATA = {
    "trending": {
        "title": "Trending Prediction Markets",
        "events": [
            {
                "question": "Will Bitcoin reach $150K by end of 2026?",
                "yes": 0.45,
                "no": 0.55,
                "volume": "$4.2M",
                "description": "Bitcoin price prediction market",
            },
            {
                "question": "Will Ethereum flip Bitcoin market cap by 2027?",
                "yes": 0.18,
                "no": 0.82,
                "volume": "$2.8M",
                "description": "Ethereum vs Bitcoin competition",
            },
            {
                "question": "Will Trump win 2026 midterms?",
                "yes": 0.52,
                "no": 0.48,
                "volume": "$8.1M",
                "description": "US politics prediction market",
            },
            {
                "question": "Will there be a Fed rate cut in Q2 2026?",
                "yes": 0.68,
                "no": 0.32,
                "volume": "$5.4M",
                "description": "Federal Reserve policy prediction",
            },
            {
                "question": "Will Apple release AR glasses in 2026?",
                "yes": 0.35,
                "no": 0.65,
                "volume": "$1.9M",
                "description": "Tech product release predictions",
            },
        ],
    },
    "crypto": {
        "title": "Cryptocurrency Markets",
        "events": [
            {
                "question": "Bitcoin > $100K by Dec 2026",
                "yes": 0.72,
                "no": 0.28,
                "volume": "$12.5M",
                "description": "Bitcoin price prediction",
            },
            {
                "question": "Ethereum > $3K by June 2026",
                "yes": 0.58,
                "no": 0.42,
                "volume": "$6.2M",
                "description": "Ethereum price prediction",
            },
            {
                "question": "Solana > $500 by June 2026",
                "yes": 0.45,
                "no": 0.55,
                "volume": "$3.8M",
                "description": "Solana price prediction",
            },
            {
                "question": " XRP > $5 by Dec 2026",
                "yes": 0.28,
                "no": 0.72,
                "volume": "$2.1M",
                "description": "XRP price prediction",
            },
            {
                "question": "New crypto ETF approved in 2026",
                "yes": 0.62,
                "no": 0.38,
                "volume": "$4.5M",
                "description": "Crypto ETF predictions",
            },
        ],
    },
    "search": {},
}


def generate_search_response(query: str, category: str = "general") -> str:
    """生成模拟的搜索结果文本"""

    base_responses = {
        "bitcoin": """**Polymarket Search: Bitcoin**

| Question | Yes | No | Volume |
|----------|-----|-----|--------|
| Will BTC reach $100K by end of 2026? | $0.72 | $0.28 | $12.5M |
| Will BTC reach $150K by end of 2026? | $0.45 | $0.55 | $4.2M |
| Will BTC hit $200K in 2026? | $0.25 | $0.75 | $2.8M |
| Will Bitcoin mining difficulty increase >50% in 2026? | $0.68 | $0.32 | $1.2M |

**Summary**: Bitcoin prediction markets show strong bullish sentiment, with 72% probability assigned to $100K+ by year-end. The most active market has $12.5M in volume.""",
        "fed": """**Polymarket Search: Federal Reserve**

| Question | Yes | No | Volume |
|----------|-----|-----|--------|
| Fed cuts rates in Q2 2026? | $0.68 | $0.32 | $5.4M |
| Fed cuts rates by 50bps in 2026? | $0.35 | $0.65 | $3.2M |
| Fed rate > 4% by June 2026? | $0.72 | $0.28 | $4.1M |
| Fed maintains rates through H1 2026? | $0.45 | $0.55 | $2.9M |

**Summary**: Markets pricing in 68% chance of Q2 rate cut, with significant volume on both sides. The debate centers on whether cuts will be 25bps or 50bps.""",
        "ai": """**Polymarket Search: AI**

| Question | Yes | No | Volume |
|----------|-----|-----|--------|
| AGI achieved by 2030? | $0.42 | $0.58 | $8.2M |
| AI creates more jobs than displaces in 2026? | $0.58 | $0.42 | $3.5M |
| Major AI breakthrough in 2026? | $0.55 | $0.45 | $5.1M |
| AI passes Turing test in 2026? | $0.38 | $0.62 | $2.8M |

**Summary**: AI prediction markets show cautious optimism. 58% believe AI will create net new jobs, while 42% see job displacement dominating.""",
        "election": """**Polymarket Search: Elections**

| Question | Yes | No | Volume |
|----------|-----|-----|--------|
| Trump wins 2026 midterms? | $0.52 | $0.48 | $8.1M |
| Democrats gain Senate seats in 2026? | $0.55 | $0.45 | $5.6M |
| Republican control of Congress in 2026? | $0.58 | $0.42 | $7.2M |
| Third party wins House seat in 2026? | $0.15 | $0.85 | $1.1M |

**Summary**: Close races across the board. 2026 midterms show competitive dynamics with no clear favorite.""",
    }

    # 尝试匹配关键词
    query_lower = query.lower()
    for key, response in base_responses.items():
        if key in query_lower:
            return response

    # 默认响应
    return f"""**Polymarket Search: {query}**

| Question | Yes | No | Volume |
|----------|-----|-----|--------|
| {query} happens in 2026? | $0.{random.randint(30, 70)} | $0.{random.randint(30, 70)} | $1-5M |

**Summary**: Market data for '{query}' shows moderate activity with balanced odds."""


@app.post("/v1/agent/chat")
async def agent_chat(request: AgentRequest, authorization: str = Header(None)):
    """模拟 UnifAI Agent 的 chat 接口"""

    # 模拟 API key 验证
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    query = request.query.lower()

    # 决定返回什么类型的响应
    if "trending" in query:
        data = MOCK_POLYMARKET_DATA["trending"]
        response = f"""## Polymarket Trending Markets

{"- " * 30}

"""
        for event in data["events"]:
            response += f"**{event['question']}**\n"
            response += f"- YES: ${event['yes']:.2f} | NO: ${event['no']:.2f}\n"
            response += f"- Volume: {event['volume']}\n\n"

    elif "crypto" in query:
        data = MOCK_POLYMARKET_DATA["crypto"]
        response = f"""## Polymarket Crypto Markets

{"- " * 30}

"""
        for event in data["events"]:
            response += f"**{event['question']}**\n"
            response += f"- YES: ${event['yes']:.2f} | NO: ${event['no']:.2f}\n"
            response += f"- Volume: {event['volume']}\n\n"

    else:
        # 搜索模式
        response = generate_search_response(request.query)

    return {
        "response": response,
        "timestamp": datetime.now().isoformat(),
        "model": "unifai-mock-v1",
    }


@app.get("/v1/agent/trending")
async def get_trending(authorization: str = Header(None)):
    """获取热门预测市场"""

    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    return {"data": MOCK_POLYMARKET_DATA["trending"], "timestamp": datetime.now().isoformat()}


@app.get("/v1/agent/crypto")
async def get_crypto(authorization: str = Header(None)):
    """获取加密货币预测市场"""

    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    return {"data": MOCK_POLYMARKET_DATA["crypto"], "timestamp": datetime.now().isoformat()}


@app.get("/v1/agent/search")
async def search(
    q: str = Query(..., description="Search query"), authorization: str = Header(None)
):
    """搜索预测市场"""

    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    return {
        "query": q,
        "response": generate_search_response(q),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

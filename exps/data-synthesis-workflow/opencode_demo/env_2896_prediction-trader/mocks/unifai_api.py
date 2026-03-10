"""
UnifAI/Polymarket API Mock - 模拟 UnifAI Agent API 用于 Polymarket 数据

从 SQLite 状态后端读取数据，与工具共享同一数据源（见 DATA_SYNTHESIS_TECH_ROUTE）。
"""

from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Query, Header
from pydantic import BaseModel

app = FastAPI(title="UnifAI Mock API")


class AgentRequest(BaseModel):
    query: str
    tools: list | None = None


def _events_to_response(events: list, title: str) -> str:
    """将 DB 事件列表格式化为 UnifAI 风格文本。"""
    out = f"## {title}\n\n"
    for e in events:
        out += f"**{e['question']}**\n"
        out += f"- YES: ${e['yes_price']:.2f} | NO: ${e['no_price']:.2f}\n"
        out += f"- Volume: {e.get('volume_display', 'N/A')}\n"
        if e.get("description"):
            out += f"- {e['description']}\n"
        out += "\n"
    return out


def _search_response(query: str) -> str:
    """从数据库搜索 Polymarket 与 Kalshi 并生成对比表格风格回复。"""
    from state import read_polymarket_events, read_kalshi_markets

    poly = read_polymarket_events(search_query=query, limit=10)
    kalshi = read_kalshi_markets(search_query=query, limit=5)

    lines = [f"**Polymarket Search: {query}**\n"]
    if poly:
        lines.append("| Question | Yes | No | Volume |")
        lines.append("|----------|-----|-----|--------|")
        for e in poly[:5]:
            lines.append(f"| {e['question'][:50]} | ${e['yes_price']:.2f} | ${e['no_price']:.2f} | {e.get('volume_display', '')} |")
    if kalshi:
        lines.append("\n**Kalshi** (CFTC-regulated)\n")
        for m in kalshi:
            lines.append(f"- {m['title']} | YES ${m['yes_price']:.2f} | Vol ${m['volume']:,}")
    if not poly and not kalshi:
        lines.append(f"No markets found for '{query}'.")
    lines.append("\n**Summary**: Data from shared state database.")
    return "\n".join(lines)


@app.post("/v1/agent/chat")
async def agent_chat(
    request: AgentRequest,
    authorization: str = Header(None),
):
    """模拟 UnifAI Agent 的 chat 接口：从状态层按 query 返回。"""
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    from state import read_polymarket_events

    query = request.query.lower()
    if "trending" in query:
        events = read_polymarket_events(category="trending")
        response = _events_to_response(events, "Polymarket Trending Markets")
    elif "crypto" in query:
        events = read_polymarket_events(category="crypto")
        response = _events_to_response(events, "Polymarket Crypto Markets")
    else:
        response = _search_response(request.query)

    return {
        "response": response,
        "timestamp": datetime.now().isoformat(),
        "model": "unifai-mock-v1",
    }


@app.get("/v1/agent/trending")
async def get_trending(authorization: str = Header(None)):
    """获取热门预测市场。"""
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    from state import read_polymarket_events

    events = read_polymarket_events(category="trending")
    data = {
        "title": "Trending Prediction Markets",
        "events": [
            {
                "question": e["question"],
                "yes": e["yes_price"],
                "no": e["no_price"],
                "volume": e.get("volume_display", ""),
                "description": e.get("description", ""),
            }
            for e in events
        ],
    }
    return {"data": data, "timestamp": datetime.now().isoformat()}


@app.get("/v1/agent/crypto")
async def get_crypto(authorization: str = Header(None)):
    """获取加密货币预测市场。"""
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    from state import read_polymarket_events

    events = read_polymarket_events(category="crypto")
    data = {
        "title": "Cryptocurrency Markets",
        "events": [
            {
                "question": e["question"],
                "yes": e["yes_price"],
                "no": e["no_price"],
                "volume": e.get("volume_display", ""),
                "description": e.get("description", ""),
            }
            for e in events
        ],
    }
    return {"data": data, "timestamp": datetime.now().isoformat()}


@app.get("/v1/agent/search")
async def search(
    q: str = Query(..., description="Search query"),
    authorization: str = Header(None),
):
    """搜索预测市场。"""
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}

    return {
        "query": q,
        "response": _search_response(q),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """健康检查。"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

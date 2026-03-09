"""
Parallel.ai API Mock - 模拟 Parallel.ai 搜索API
"""

import random
import uuid
from datetime import datetime
from fastapi import FastAPI, Header
from pydantic import BaseModel

app = FastAPI(title="Parallel.ai Mock API")


class SearchRequest(BaseModel):
    objective: str
    max_results: int = 10
    mode: str = "one-shot"


MOCK_SEARCH_DATA = {
    "anthropic": [
        {
            "title": "Dario Amodei - CEO of Anthropic",
            "url": "https://en.wikipedia.org/wiki/Dario_Amodei",
            "excerpts": [
                "Dario Amodei is the CEO and co-founder of Anthropic, an AI safety and research company.",
                "Under his leadership, Anthropic has developed Claude, a family of large language models.",
            ],
            "publish_date": "2024-01-15",
        },
        {
            "title": "Anthropic - AI Safety Company",
            "url": "https://www.anthropic.com",
            "excerpts": [
                "Anthropic is an AI safety and research company working to build reliable, beneficial AI systems.",
            ],
            "publish_date": "2024-02-01",
        },
    ],
    "ai": [
        {
            "title": "The Future of AI: 2024 Research Report",
            "url": "https://example.com/ai-future-2024",
            "excerpts": [
                "Artificial intelligence continues to advance rapidly, with new breakthroughs in reasoning and multimodal capabilities.",
            ],
            "publish_date": "2024-11-20",
        },
    ],
    "default": [
        {
            "title": f"Search Result {i}",
            "url": f"https://example.com/result-{i}",
            "excerpts": [
                f"This is a mock search result for the query about {random.choice(['technology', 'science', 'business'])}.",
            ],
            "publish_date": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        }
        for i in range(1, 6)
    ],
}


def generate_search_results(query: str, max_results: int, mode: str) -> dict:
    query_lower = query.lower()
    results = []

    for key, data in MOCK_SEARCH_DATA.items():
        if key in query_lower:
            results = data[:max_results]
            break

    if not results:
        results = MOCK_SEARCH_DATA["default"][:max_results]

    return {
        "search_id": f"search_{uuid.uuid4().hex[:12]}",
        "results": results,
        "usage": {"tokens": random.randint(1000, 5000), "searches": random.randint(1, 3)},
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/search")
async def search(request: SearchRequest, authorization: str = Header(None)):
    if not authorization or "Bearer" not in authorization:
        return {"error": "Unauthorized", "status_code": 401}
    return generate_search_results(request.objective, request.max_results, request.mode)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

"""
SearXNG API Mock - 模拟 SearXNG 自托管搜索聚合器

SearXNG 查询多个搜索引擎：Google, Bing, Brave, Startpage, DuckDuckGo, Wikipedia
"""

from fastapi import FastAPI, Query
from typing import List, Dict
import random
from datetime import datetime

app = FastAPI(title="SearXNG Mock API")

MOCK_RESULTS = {
    "python": [
        {
            "title": "Python Tutorial - Official Documentation",
            "url": "https://docs.python.org/3/tutorial/",
            "content": "The official Python tutorial is a great way to learn Python programming from scratch.",
            "engine": "google",
        },
        {
            "title": "Python for Beginners",
            "url": "https://www.w3schools.com/python/",
            "content": "W3Schools offers free Python tutorials with examples and exercises.",
            "engine": "bing",
        },
        {
            "title": "Learn Python - Programming with Mosh",
            "url": "https://programmingwithmosh.com/python/python-tutorial-beginners/",
            "content": "A comprehensive Python tutorial for beginners covering all fundamentals.",
            "engine": "brave",
        },
        {
            "title": "Python (programming language) - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
            "content": "Python is a high-level, general-purpose programming language known for its readability.",
            "engine": "wikipedia",
        },
        {
            "title": "Real Python - Python Tutorials",
            "url": "https://realpython.com/",
            "content": "Real Python is a platform for Python developers to learn and share.",
            "engine": "duckduckgo",
        },
    ],
    "machine learning": [
        {
            "title": "Machine Learning - Stanford Online",
            "url": "https://www.coursera.org/learn/machine-learning",
            "content": "Learn the fundamentals of machine learning from Stanford professor Andrew Ng.",
            "engine": "google",
        },
        {
            "title": "TensorFlow Documentation",
            "url": "https://www.tensorflow.org/guide",
            "content": "TensorFlow is an open source machine learning framework developed by Google.",
            "engine": "google",
        },
        {
            "title": "PyTorch Documentation",
            "url": "https://pytorch.org/docs/",
            "content": "PyTorch is an open source machine learning library based on the Torch library.",
            "engine": "bing",
        },
        {
            "title": "Machine learning - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Machine_learning",
            "content": "Machine learning is a field of inquiry devoted to understanding and building methods that learn.",
            "engine": "wikipedia",
        },
    ],
    "github": [
        {
            "title": "torvalds/linux",
            "url": "https://github.com/torvalds/linux",
            "content": "Linux kernel source code repository",
            "engine": "google",
        },
        {
            "title": "facebook/react",
            "url": "https://github.com/facebook/react",
            "content": "A declarative, efficient, and flexible JavaScript library for building user interfaces.",
            "engine": "bing",
        },
        {
            "title": "microsoft/vscode",
            "url": "https://github.com/microsoft/vscode",
            "content": "Code editing. Redefined. Visual Studio Code.",
            "engine": "brave",
        },
        {
            "title": "github/hub",
            "url": "https://github.com/github/hub",
            "content": "hub is a command line tool that wraps git in order to extend it with extra features.",
            "engine": "duckduckgo",
        },
    ],
}

ENGINES = ["google", "bing", "brave", "startpage", "duckduckgo", "wikipedia"]


def generate_mock_results(query: str, count: int) -> List[Dict]:
    """Generate mock search results for a query"""
    query_lower = query.lower()

    for key, results in MOCK_RESULTS.items():
        if key in query_lower:
            return results[:count]

    num_results = min(count, 5)
    return [
        {
            "title": f"{query.title()} - Result {i + 1}",
            "url": f"https://example.com/{query.lower().replace(' ', '-')}/{i + 1}",
            "content": f"This is a mock search result for '{query}'. It contains relevant information about the topic.",
            "engine": random.choice(ENGINES),
        }
        for i in range(num_results)
    ]


@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    format: str = Query("json", description="Output format"),
    limit: int = Query(10, description="Max results"),
):
    """SearXNG search endpoint"""
    results = generate_mock_results(q, limit)

    return {
        "query": q,
        "format": format,
        "results": results,
        "number_of_results": len(results),
        "infoboxes": [],
        "suggestions": [],
        "answers": [],
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8888)

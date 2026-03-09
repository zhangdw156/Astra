"""
UniFuncs API Mock - 模拟 UniFuncs 搜索API

UniFuncs 提供实时网络搜索服务，支持全球和中国地域搜索。
"""

from typing import Optional
from fastapi import FastAPI, Query, Header
from pydantic import BaseModel
import random
from datetime import datetime

app = FastAPI(title="UniFuncs Mock API")


class WebPage(BaseModel):
    name: str
    url: str
    snippet: str
    siteName: Optional[str] = None


class SearchResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict


MOCK_RESULTS = {
    "global": [
        [
            WebPage(
                name="Python Documentation",
                url="https://docs.python.org/3/",
                snippet="Official Python programming language documentation. Learn Python syntax, built-in functions, modules, and more.",
                siteName="Python.org",
            ),
            WebPage(
                name="Python Tutorial - W3Schools",
                url="https://www.w3schools.com/python/",
                snippet="Python tutorial for beginners. Learn Python programming with examples and exercises.",
                siteName="W3Schools",
            ),
            WebPage(
                name="Real Python - Python Tutorials",
                url="https://realpython.com/",
                snippet="Free Python tutorials and guides. From beginner to advanced Python programming.",
                siteName="Real Python",
            ),
            WebPage(
                name="Python GitHub",
                url="https://github.com/python",
                snippet="Python programming language official GitHub repository. Contribute to Python development.",
                siteName="GitHub",
            ),
            WebPage(
                name="PyPI - Python Package Index",
                url="https://pypi.org/",
                snippet="Python Package Index. Find, install and publish Python packages.",
                siteName="PyPI",
            ),
        ],
        [
            WebPage(
                name="Machine Learning Tutorial",
                url="https://www.tensorflow.org/tutorials",
                snippet="Learn machine learning with TensorFlow. Build neural networks and ML models.",
                siteName="TensorFlow",
            ),
            WebPage(
                name="Deep Learning Courses",
                url="https://www.coursera.org/browse/data-science/machine-learning",
                snippet="Online machine learning courses from top universities and companies.",
                siteName="Coursera",
            ),
            WebPage(
                name="Scikit-learn Documentation",
                url="https://scikit-learn.org/",
                snippet="Simple and efficient tools for data mining and analysis.",
                siteName="Scikit-learn",
            ),
        ],
        [
            WebPage(
                name="Latest AI News",
                url="https://openai.com/blog",
                snippet="Latest news and research from OpenAI. GPT models, safety research, and AI advancements.",
                siteName="OpenAI",
            ),
            WebPage(
                name="AI Research Papers",
                url="https://arxiv.org/list/cs.AI/recent",
                snippet="Recent papers on artificial intelligence and machine learning.",
                siteName="arXiv",
            ),
        ],
    ],
    "cn": [
        [
            WebPage(
                name="Python教程 - 菜鸟教程",
                url="https://www.runoob.com/python3/",
                snippet="Python3基础教程，适合初学者学习Python编程。",
                siteName="菜鸟教程",
            ),
            WebPage(
                name="Python - 廖雪峰的官方网站",
                url="https://www.liaoxuefeng.com/wiki/1016959663602400",
                snippet="Python入门教程，全面介绍Python语法和常用模块。",
                siteName="廖雪峰的博客",
            ),
            WebPage(
                name="Python中文社区",
                url="https://python.cn/",
                snippet="Python中文社区，提供教程、问答和资源下载。",
                siteName="Python中文网",
            ),
        ],
        [
            WebPage(
                name="机器学习 - 百度百科",
                url="https://baike.baidu.com/item/机器学习",
                snippet="机器学习是人工智能的一个分支，专门研究计算机怎样模拟或实现人类的学习行为。",
                siteName="百度百科",
            ),
            WebPage(
                name="深度学习入门 - 知乎",
                url="https://zhuanlan.zhihu.com/p/深度学习",
                snippet="深度学习入门指南，从基础概念到实践项目。",
                siteName="知乎",
            ),
        ],
    ],
}


@app.post("/api/web-search/search")
async def search(
    query: str = Query(...),
    area: str = Query("global"),
    page: int = Query(1),
    count: int = Query(10),
    format: str = Query("json"),
    includeImages: bool = Query(False),
    freshness: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
):
    """搜索接口"""
    if not query:
        return {"code": -30001, "message": "Search keyword is invalid", "data": {}}

    if not authorization or not authorization.startswith("Bearer "):
        return {"code": -20021, "message": "API key is invalid or expired", "data": {}}

    query_lower = query.lower()

    topic_index = 0
    if any(k in query_lower for k in ["machine", "learn", "ml", "ai", "deep"]):
        topic_index = 1
    elif any(k in query_lower for k in ["news", "最新", "news"]):
        topic_index = 2

    if area == "cn":
        topic_index = min(topic_index, len(MOCK_RESULTS["cn"]) - 1)
        results = MOCK_RESULTS["cn"][topic_index]
    else:
        topic_index = min(topic_index, len(MOCK_RESULTS["global"]) - 1)
        results = MOCK_RESULTS["global"][topic_index]

    results = results[:count]

    return {
        "code": 0,
        "message": "success",
        "data": {
            "webPages": [r.model_dump() for r in results],
            "total": len(results),
            "query": query,
            "area": area,
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

"""
UniFuncs API Mock - 模拟 UniFuncs 网页阅读 API

UniFuncs 是一个网页阅读服务，支持读取网页、PDF、Word 等文档，并使用 AI 进行内容提取。
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import random

app = FastAPI(title="UniFuncs Mock API")


class ReadRequest(BaseModel):
    url: str
    format: str = "md"
    liteMode: bool = False
    includeImages: bool = True
    onlyCSSSelectors: Optional[List[str]] = None
    waitForCSSSelectors: Optional[List[str]] = None
    excludeCSSSelectors: Optional[List[str]] = None
    linkSummary: bool = False
    ignoreCache: bool = False
    readTimeout: int = 120000
    topic: Optional[str] = None
    preserveSource: bool = False
    temperature: float = 0.2
    extractTimeout: int = 120000


MOCK_CONTENT = {
    "example.com": """# Example Domain

This domain is for use in illustrative examples in documents. You may use this
domain in literature without prior coordination or asking for permission.

## More Information

For more information, please visit [Example](https://example.com).

This is a mock response from the UniFuncs API demonstrating the content extraction
capabilities. The actual API would return the full HTML content parsed to markdown.""",
    "github.com": """# GitHub

GitHub is a code hosting platform for version control and collaboration. It's used
by millions of developers to share code, build software, and manage projects.

## Features

- Git repositories
- Pull requests
- Issues tracking
- Actions automation

This is a mock response for demonstration purposes.""",
    "default": """# Web Page Content

This is a mock response from the UniFuncs API. The actual service would return the
real content from the requested URL.

## Summary

The page contains information about the requested topic. The content has been
extracted and formatted using AI-powered parsing.

## Key Points

- Point one about the content
- Point two about the content  
- Point three about the content

## Conclusion

This demonstrates the UniFuncs web reader capabilities for extracting content
from various web pages, PDFs, and documents.""",
}


def generate_mock_content(url: str, topic: Optional[str] = None) -> str:
    """根据 URL 生成模拟内容"""

    url_lower = url.lower()

    for domain, content in MOCK_CONTENT.items():
        if domain in url_lower:
            if topic:
                return f"## Extracted: {topic}\n\n{content}\n\n*(Source: {url})*"
            return content

    if topic:
        return f"## Extracted: {topic}\n\n{MOCK_CONTENT['default']}\n\n*(Source: {url})*"

    return MOCK_CONTENT["default"]


@app.post("/api/web-reader/read")
async def read_url(request: ReadRequest, authorization: str = Header(None)):
    """模拟 UniFuncs Web Reader API"""

    if not authorization or "Bearer" not in authorization:
        return {"code": -20021, "message": "API Key invalid or expired. Please check your API key."}

    api_key = authorization.replace("Bearer ", "").strip()
    if api_key == "mock-api-key" or api_key:
        pass
    else:
        return {"code": -20021, "message": "API Key invalid or expired. Please check your API key."}

    content = generate_mock_content(request.url, request.topic)

    return {
        "code": 0,
        "message": "success",
        "data": content,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

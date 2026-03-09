"""
UniFuncs Search Tool - 使用 UniFuncs API 进行实时网络搜索

支持全球和中国地域搜索，获取最新网络内容和新闻。
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error

TOOL_SCHEMA = {
    "name": "search",
    "description": "Perform real-time web search using UniFuncs API. "
    "Supports global and China regional search. "
    "Use this when user wants to search the web, find information, or get latest news. "
    "Returns web pages, news, and optionally images.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query/keywords"},
            "area": {
                "type": "string",
                "enum": ["global", "cn"],
                "default": "global",
                "description": "Search region: global (worldwide) or cn (China)",
            },
            "freshness": {
                "type": "string",
                "enum": ["Day", "Week", "Month", "Year"],
                "default": "",
                "description": "Result freshness filter",
            },
            "include_images": {
                "type": "boolean",
                "default": False,
                "description": "Whether to include image search results",
            },
            "page": {"type": "integer", "default": 1, "description": "Page number for pagination"},
            "count": {
                "type": "integer",
                "default": 10,
                "description": "Number of results per page (1-50)",
            },
        },
        "required": ["query"],
    },
}

UNIFUNCS_API_BASE = os.environ.get("UNIFUNCS_API_BASE", "http://localhost:8001")
UNIFUNCS_API_KEY = os.environ.get("UNIFUNCS_API_KEY", "mock-api-key")


def execute(
    query: str,
    area: str = "global",
    freshness: str = "",
    include_images: bool = False,
    page: int = 1,
    count: int = 10,
) -> str:
    """
    使用 UniFuncs API 执行搜索

    Args:
        query: 搜索关键词
        area: 搜索地区 (global/cn)
        freshness: 结果时效性
        include_images: 是否包含图像
        page: 页码
        count: 每页数量

    Returns:
        格式化的搜索结果
    """
    if not query or not query.strip():
        return "Error: Search query cannot be empty"

    if not 1 <= count <= 50:
        return "Error: count must be between 1 and 50"

    try:
        url = f"{UNIFUNCS_API_BASE}/api/web-search/search"

        data = {
            "query": query,
            "area": area,
            "page": page,
            "count": count,
            "format": "json",
            "includeImages": include_images,
        }

        if freshness:
            data["freshness"] = freshness

        json_data = json.dumps(data).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {UNIFUNCS_API_KEY}",
        }

        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode("utf-8")
            result = json.loads(response_data)

        code = result.get("code", -1)
        if code != 0:
            error_msg = result.get("message", "Unknown error")
            return f"Search error [{code}]: {error_msg}"

        data = result.get("data", {})
        web_pages = data.get("webPages", [])

        if not web_pages:
            return f"No results found for: {query}"

        output = []
        output.append(f"## Search Results for: {query}")
        output.append(f"Region: {area.upper()}")
        if freshness:
            output.append(f"Freshness: {freshness}")
        output.append(f"\nFound {len(web_pages)} results:\n")

        for i, page_data in enumerate(web_pages, 1):
            output.append(f"### {i}. {page_data.get('name', 'No title')}")
            output.append(f"**URL**: {page_data.get('url', '')}")
            if page_data.get("siteName"):
                output.append(f"**Source**: {page_data.get('siteName')}")
            output.append(f"\n{page_data.get('snippet', page_data.get('summary', ''))}\n")

        return "\n".join(output)

    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"Network Error: {e.reason}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    print(execute("Python programming"))

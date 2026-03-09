"""
Read Tool - 使用 UniFuncs API 读取网页、PDF、Word 等文档内容

读取网页、PDF、Word 等文档内容，支持 AI 内容提取。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "read",
    "description": "Read web pages, PDF, Word documents using UniFuncs API with AI content extraction. "
    "Use this when you need to fetch, extract, or summarize content from URLs. "
    "Supports markdown, text output, CSS filtering, and topic-based extraction.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to read (web page, PDF, Word doc, etc.)"},
            "format": {
                "type": "string",
                "enum": ["markdown", "md", "text", "txt"],
                "default": "md",
                "description": "Output format: markdown, md, text, or txt",
            },
            "lite_mode": {
                "type": "boolean",
                "default": False,
                "description": "Enable lite mode - only keep readable content",
            },
            "include_images": {
                "type": "boolean",
                "default": True,
                "description": "Include images in the output",
            },
            "only_css_selectors": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Only include elements matching these CSS selectors",
            },
            "exclude_css_selectors": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
                "description": "Exclude elements matching these CSS selectors",
            },
            "link_summary": {
                "type": "boolean",
                "default": False,
                "description": "Append all page links to the end of content",
            },
            "ignore_cache": {
                "type": "boolean",
                "default": False,
                "description": "Ignore cached content and re-fetch",
            },
            "topic": {
                "type": "string",
                "description": "Extract specific topic content using AI (uses LLM)",
            },
            "preserve_source": {
                "type": "boolean",
                "default": False,
                "description": "Add source reference to each paragraph when using topic extraction",
            },
            "temperature": {
                "type": "number",
                "default": 0.2,
                "description": "LLM randomness for topic extraction (0.0-1.5)",
            },
        },
        "required": ["url"],
    },
}

UNIFUNCS_API_BASE = os.environ.get("UNIFUNCS_API_BASE", "http://localhost:8001")
UNIFUNCS_API_KEY = os.environ.get("UNIFUNCS_API_KEY", "mock-api-key")


def execute(
    url: str,
    format: str = "md",
    lite_mode: bool = False,
    include_images: bool = True,
    only_css_selectors: list = None,
    exclude_css_selectors: list = None,
    link_summary: bool = False,
    ignore_cache: bool = False,
    topic: str = None,
    preserve_source: bool = False,
    temperature: float = 0.2,
) -> str:
    """
    Read a URL using UniFuncs API

    Args:
        url: URL to read
        format: Output format (markdown, md, text, txt)
        lite_mode: Enable lite mode
        include_images: Include images in output
        only_css_selectors: CSS selectors to include
        exclude_css_selectors: CSS selectors to exclude
        link_summary: Append links to end
        ignore_cache: Ignore cached content
        topic: Extract specific topic using AI
        preserve_source: Add source reference per paragraph
        temperature: LLM temperature for topic extraction

    Returns:
        Formatted content from the URL
    """
    if only_css_selectors is None:
        only_css_selectors = []
    if exclude_css_selectors is None:
        exclude_css_selectors = []

    api_url = f"{UNIFUNCS_API_BASE}/api/web-reader/read"

    data = {
        "url": url,
        "format": format,
        "liteMode": lite_mode,
        "includeImages": include_images,
        "linkSummary": link_summary,
        "ignoreCache": ignore_cache,
    }

    if only_css_selectors:
        data["onlyCSSSelectors"] = only_css_selectors
    if exclude_css_selectors:
        data["excludeCSSSelectors"] = exclude_css_selectors
    if topic:
        data["topic"] = topic
        data["preserveSource"] = preserve_source
        data["temperature"] = temperature

    json_data = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {UNIFUNCS_API_KEY}"}

    req = urllib.request.Request(api_url, data=json_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response_data = response.read().decode("utf-8")
            try:
                result = json.loads(response_data)
                if result.get("code") != 0:
                    return f"Error: {result.get('message', 'Unknown error')} (code: {result.get('code')})"
                content = result.get("data", "")
                return content if content else response_data
            except json.JSONDecodeError:
                return response_data
    except urllib.request.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_msg)
            return f"HTTP {e.code}: {error_data.get('message', error_msg)}"
        except json.JSONDecodeError:
            return f"HTTP {e.code}: {error_msg}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    print(execute("https://example.com"))

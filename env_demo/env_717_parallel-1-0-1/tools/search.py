"""
Parallel.ai Search Tool - High-accuracy web search via Parallel.ai API
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "search",
    "description": "High-accuracy web search via Parallel.ai API. "
    "Optimized for AI agents with rich excerpts and citations. "
    "Use this for deep research, company/person research, fact-checking, "
    "and complex queries requiring multi-hop reasoning.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "objective": {
                "type": "string",
                "description": "Search query/objective (e.g., 'Who is the CEO of Anthropic?', 'latest AI news')",
            },
            "max_results": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of results to return",
            },
            "mode": {
                "type": "string",
                "default": "one-shot",
                "description": "Search mode: 'one-shot' for simple queries, 'agentic' for complex research",
                "enum": ["one-shot", "agentic"],
            },
        },
        "required": ["objective"],
    },
}

PARALLEL_API_BASE = os.environ.get("PARALLEL_API_BASE", "http://localhost:8001")
PARALLEL_API_KEY = os.environ.get("PARALLEL_API_KEY", "mock-api-key")


def execute(objective: str, max_results: int = 10, mode: str = "one-shot") -> str:
    """
    Search using Parallel.ai API

    Args:
        objective: Search query/objective
        max_results: Maximum number of results
        mode: Search mode (one-shot or agentic)

    Returns:
        Formatted search results
    """
    output = f"## 🔍 Parallel.ai Search: {objective}\n\n"

    try:
        url = f"{PARALLEL_API_BASE}/search"

        payload = {"objective": objective, "max_results": max_results, "mode": mode}

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PARALLEL_API_KEY}",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode())

        output += f"**Search ID:** {result.get('search_id', 'N/A')}\n\n"
        output += "### Results\n\n"

        results = result.get("results", [])
        if not results:
            output += "No results found.\n"
        else:
            for i, r in enumerate(results, 1):
                title = r.get("title", "No title")
                url = r.get("url", "")
                excerpts = r.get("excerpts", [])
                publish_date = r.get("publish_date", "")

                date_str = f" ({publish_date})" if publish_date else ""
                output += f"**{i}. [{title}]({url})**{date_str}\n"

                if excerpts:
                    for exc in excerpts[:2]:
                        exc_clean = exc.replace("\n", " ").strip()[:300]
                        output += f"   > {exc_clean}...\n"
                output += "\n"

        usage = result.get("usage", {})
        if usage:
            output += f"**Usage:** "
            usage_parts = []
            for k, v in usage.items():
                usage_parts.append(f"{k}: {v}")
            output += ", ".join(usage_parts) + "\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("Who is the CEO of Anthropic?", max_results=3))

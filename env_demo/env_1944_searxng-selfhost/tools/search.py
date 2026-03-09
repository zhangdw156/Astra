"""
Search Tool - Web search via SearXNG with fallback

Primary: local SearXNG instance (Google, Bing, Brave, Startpage, DDG, Wikipedia)
Fallback: Wikipedia + GitHub APIs
"""

import json
import os
import re
import urllib.parse
import urllib.request

TOOL_SCHEMA = {
    "name": "search",
    "description": "Search the web using SearXNG self-hosted search aggregator. "
    "Queries multiple search engines (Google, Bing, Brave, Startpage, DuckDuckGo, Wikipedia) "
    "and returns aggregated results. Falls back to Wikipedia + GitHub if SearXNG is unavailable. "
    "No API keys required.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'python tutorial', 'latest news', 'github repository')",
            },
            "count": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of results to return",
            },
        },
        "required": ["query"],
    },
}

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")
WIKIPEDIA_URL = "https://en.wikipedia.org/w/api.php"
GITHUB_URL = "https://api.github.com/search/repositories"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def search_searxng(query: str, count: int = 10):
    """Query local SearXNG instance"""
    url = f"{SEARXNG_URL}/search?q={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            return [
                {
                    "title": x.get("title", ""),
                    "url": x.get("url", ""),
                    "snippet": x.get("content", "")[:200],
                    "engine": x.get("engine", "?"),
                }
                for x in d.get("results", [])[:count]
            ]
    except Exception as e:
        return None


def search_wikipedia(query: str, count: int = 5):
    """Wikipedia API fallback"""
    url = f"{WIKIPEDIA_URL}?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit={count}&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
            return [
                {
                    "title": x["title"],
                    "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(x['title'].replace(' ', '_'))}",
                    "snippet": re.sub(r"<[^>]+>", "", x.get("snippet", "")),
                    "engine": "wikipedia",
                }
                for x in d["query"]["search"][:count]
            ]
    except:
        return []


def search_github(query: str, count: int = 5):
    """GitHub Search API fallback"""
    url = f"{GITHUB_URL}?q={urllib.parse.quote(query)}&per_page={count}"
    req = urllib.request.Request(
        url, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            d = json.loads(r.read())
            return [
                {
                    "title": x["full_name"],
                    "url": x["html_url"],
                    "snippet": (x.get("description") or "")[:200],
                    "engine": "github",
                }
                for x in d.get("items", [])[:count]
            ]
    except:
        return []


def execute(query: str, count: int = 10) -> str:
    """
    Search the web via SearXNG with fallback to Wikipedia + GitHub

    Args:
        query: Search query
        count: Maximum number of results

    Returns:
        Formatted search results
    """
    results = search_searxng(query, count)

    if results is not None:
        output = f"## Search Results: {query}\n\n"
        output += f"*Found {len(results)} results via SearXNG*\n\n"

        for i, r in enumerate(results, 1):
            output += f"### {i}. [{r['engine']}] {r['title']}\n"
            output += f"**URL**: {r['url']}\n"
            if r.get("snippet"):
                output += f"**Snippet**: {r['snippet'][:200]}\n"
            output += "\n"

        return output

    output = f"## Search Results: {query}\n\n"
    output += "*SearXNG unavailable - using fallback (Wikipedia + GitHub)*\n\n"

    wp = search_wikipedia(query, count)
    gh = search_github(query, min(5, count))
    results = (wp + gh)[:count]

    if not results:
        return f"No results found for: {query}"

    for i, r in enumerate(results, 1):
        output += f"### {i}. [{r['engine']}] {r['title']}\n"
        output += f"**URL**: {r['url']}\n"
        if r.get("snippet"):
            output += f"**Snippet**: {r['snippet'][:200]}\n"
        output += "\n"

    return output


if __name__ == "__main__":
    print(execute("python tutorial"))

"""
Search Assets Tool - 搜索资产

按名称、股票代码或账户搜索资产和债务。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "search_assets",
    "description": "Search for assets and debts by name, ticker symbol, or account. "
    "Use this to quickly find specific holdings across all sheets and categories.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (name, ticker, or account name)",
            },
            "portfolio_id": {
                "type": "string",
                "description": "Portfolio ID. If not provided, auto-selects for single-portfolio accounts",
            },
        },
        "required": ["query"],
    },
}

KUBERA_API_BASE = os.environ.get("KUBERA_API_BASE", "http://localhost:8003")
KUBERA_API_KEY = os.environ.get("KUBERA_API_KEY", "mock-api-key")
KUBERA_SECRET = os.environ.get("KUBERA_SECRET", "mock-secret")


def make_request(path, method="GET", body=None):
    """Make authenticated request to Kubera API"""
    timestamp = str(math.floor(time.time()))
    body_data = json.dumps(body, separators=(",", ":")) if body else ""
    data = f"{KUBERA_API_KEY}{timestamp}{method}{path}{body_data}"
    signature = hmac.new(KUBERA_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        f"{KUBERA_API_BASE}{path}",
        data=body_data.encode() if body else None,
        headers={
            "Content-Type": "application/json",
            "x-api-token": KUBERA_API_KEY,
            "x-timestamp": timestamp,
            "x-signature": signature,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def get_portfolio_id(requested_id=None):
    """Get portfolio ID, auto-selecting if needed"""
    if requested_id:
        return requested_id
    result = make_request("/api/v3/data/portfolio")
    portfolios = result.get("data", [])
    if not portfolios:
        return None
    if len(portfolios) == 1:
        return portfolios[0]["id"]
    return None


def execute(query: str, portfolio_id: str = None) -> str:
    """
    Search assets

    Args:
        query: Search query
        portfolio_id: Optional portfolio ID

    Returns:
        格式化的搜索结果
    """
    pid = get_portfolio_id(portfolio_id)
    if not pid:
        return "Error: Could not determine portfolio ID. Please specify portfolio_id."

    output = f'## Search Results: "{query}"\n\n'

    result = make_request(f"/api/v3/data/portfolio/{pid}")

    if "error" in result:
        return f"Error: {result['error']}"

    d = result.get("data", {})
    q = query.lower()

    matches = [
        a
        for a in d.get("asset", []) + d.get("debt", [])
        if q in a.get("name", "").lower()
        or q in a.get("ticker", "").lower()
        or q in a.get("sectionName", "").lower()
    ]

    if not matches:
        return output + "No matches found."

    output += f"Found {len(matches)} matches:\n\n"

    for a in sorted(matches, key=lambda x: -abs(x["value"]["amount"])):
        val = a["value"]["amount"]
        output += f"**{a['name'][:45]}**\n"
        output += f"- Value: ${val:,.2f}\n"
        output += f"- Sheet: {a.get('sheetName', '?')}\n"
        if a.get("ticker"):
            output += f"- Ticker: {a['ticker']}\n"
        output += "\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin"))

"""
List Assets Tool - 列出资产

列出投资组合中的所有资产，支持按sheet过滤和排序。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "list_assets",
    "description": "List all assets in a portfolio, optionally filtered by sheet (e.g., Crypto, Equities) "
    "and sorted by value, name, or gain. Use this to get a detailed view of holdings "
    "organized by asset class or category.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "portfolio_id": {
                "type": "string",
                "description": "Portfolio ID. If not provided, auto-selects for single-portfolio accounts",
            },
            "sheet": {
                "type": "string",
                "description": "Filter by sheet name (e.g., Crypto, Equities, Retirement, Real Estate, Cash)",
            },
            "sort": {
                "type": "string",
                "enum": ["value", "name", "gain"],
                "default": "value",
                "description": "Sort order: value (highest first), name (alphabetical), gain (highest gain first)",
            },
        },
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


def execute(portfolio_id: str = None, sheet: str = None, sort: str = "value") -> str:
    """
    List assets

    Args:
        portfolio_id: Optional portfolio ID
        sheet: Optional sheet filter
        sort: Sort order (value, name, gain)

    Returns:
        格式化的资产列表
    """
    pid = get_portfolio_id(portfolio_id)
    if not pid:
        return "Error: Could not determine portfolio ID. Please specify portfolio_id."

    output = "## Portfolio Assets\n\n"
    if sheet:
        output += f"*Filtered by: {sheet}*\n\n"

    result = make_request(f"/api/v3/data/portfolio/{pid}")

    if "error" in result:
        return f"Error: {result['error']}"

    d = result.get("data", {})
    assets = d.get("asset", [])

    if sheet:
        assets = [a for a in assets if sheet.lower() in a.get("sheetName", "").lower()]

    sort_key = {
        "value": lambda x: -x["value"]["amount"],
        "name": lambda x: x["name"].lower(),
        "gain": lambda x: -(x["value"]["amount"] - x.get("cost", {}).get("amount", 0)),
    }.get(sort, lambda x: -x["value"]["amount"])
    assets.sort(key=sort_key)

    output += f"Total assets: {len(assets)}\n\n"

    for a in assets:
        val = a["value"]["amount"]
        cost = a.get("cost", {}).get("amount", 0)
        gain = val - cost if cost else None
        gain_str = f"  gain: ${gain:>+,.2f}" if gain is not None and cost > 0 else ""
        output += f"**{a['name'][:45]}**\n"
        output += f"- Value: ${val:,.2f}{gain_str}\n"
        output += f"- Sheet: {a.get('sheetName', '?')}\n"
        if a.get("ticker"):
            output += f"- Ticker: {a['ticker']}\n"
        output += "\n"

    return output


if __name__ == "__main__":
    print(execute())

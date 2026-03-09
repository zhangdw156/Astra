"""
Get Portfolio JSON Tool - 获取完整投资组合JSON

获取投资组合的完整原始JSON数据，用于详细分析。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "get_portfolio_json",
    "description": "Get full portfolio data as raw JSON. "
    "Use this for complete portfolio analysis including all assets, debts, "
    "insurance, documents and detailed field values. Returns the raw API response.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "portfolio_id": {
                "type": "string",
                "description": "Portfolio ID. If not provided, auto-selects for single-portfolio accounts",
            }
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


def execute(portfolio_id: str = None) -> str:
    """
    Get portfolio as JSON

    Args:
        portfolio_id: Optional portfolio ID

    Returns:
        完整的投资组合JSON
    """
    pid = get_portfolio_id(portfolio_id)
    if not pid:
        return "Error: Could not determine portfolio ID. Please specify portfolio_id."

    result = make_request(f"/api/v3/data/portfolio/{pid}")

    if "error" in result:
        return f"Error: {result['error']}"

    return json.dumps(result, indent=2)


if __name__ == "__main__":
    print(execute())

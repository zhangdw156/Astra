"""
Get Summary Tool - 获取投资组合摘要

获取投资组合的净资产、总资产、债务、配置和顶级持仓。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "get_summary",
    "description": "Get net worth summary with asset allocation and top holdings. "
    "Use this to get a quick overview of a portfolio including total assets, debts, "
    "net worth, allocation by asset class, and top 10 holdings by value.",
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
    Get portfolio summary

    Args:
        portfolio_id: Optional portfolio ID

    Returns:
        格式化的投资组合摘要
    """
    pid = get_portfolio_id(portfolio_id)
    if not pid:
        return "Error: Could not determine portfolio ID. Please specify portfolio_id."

    output = f"## Portfolio Summary\n\n"

    result = make_request(f"/api/v3/data/portfolio/{pid}")

    if "error" in result:
        return f"Error: {result['error']}"

    d = result.get("data", {})

    output += f"**Portfolio**: {d.get('name', 'N/A')} ({d.get('ticker', 'USD')})\n\n"

    output += "### Financial Overview\n\n"
    output += f"- Net Worth: ${d.get('netWorth', 0):,.2f}\n"
    output += f"- Total Assets: ${d.get('assetTotal', 0):,.2f}\n"
    output += f"- Total Debts: ${d.get('debtTotal', 0):,.2f}\n"
    output += f"- Cost Basis: ${d.get('costBasis', 0):,.2f}\n"
    output += f"- Unrealized Gain: ${d.get('unrealizedGain', 0):,.2f}\n\n"

    alloc = d.get("allocationByAssetClass", {})
    if alloc:
        output += "### Asset Allocation\n\n"
        for k, v in alloc.items():
            if v and v > 0:
                output += f"- {k}: {v:.1f}%\n"
        output += "\n"

    sorted_assets = sorted(d.get("asset", []), key=lambda x: -x["value"]["amount"])
    output += "### Top 10 Holdings\n\n"
    for i, a in enumerate(sorted_assets[:10], 1):
        val = a["value"]["amount"]
        output += f"{i}. **{a['name'][:40]}**: ${val:,.2f} [{a.get('sheetName', '?')}]\n"

    if d.get("debt"):
        output += "\n### Debts\n\n"
        for debt in d["debt"]:
            output += f"- {debt['name'][:50]}: ${debt['value']['amount']:,.2f}\n"

    return output


if __name__ == "__main__":
    print(execute())

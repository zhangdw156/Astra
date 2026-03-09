"""
List Portfolios Tool - 列出所有投资组合

获取用户账户下的所有投资组合列表。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "list_portfolios",
    "description": "List all portfolios in the Kubera account. "
    "Use this first to find portfolio IDs for other operations. "
    "Works for single and multi-portfolio accounts.",
    "inputSchema": {"type": "object", "properties": {}},
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


def execute() -> str:
    """
    List all portfolios

    Returns:
        格式化的投资组合列表
    """
    output = "## Kubera Portfolios\n\n"

    result = make_request("/api/v3/data/portfolio")

    if "error" in result:
        return f"Error: {result['error']}"

    portfolios = result.get("data", [])
    if not portfolios:
        return "No portfolios found."

    for p in portfolios:
        output += f"**{p['name']}**\n"
        output += f"- ID: `{p['id']}`\n"
        output += f"- Currency: {p.get('currency', 'USD')}\n\n"

    return output


if __name__ == "__main__":
    print(execute())

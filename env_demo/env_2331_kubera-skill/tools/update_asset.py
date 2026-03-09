"""
Update Asset Tool - 更新资产

更新资产或债务的值、名称、成本或描述。
"""

import json
import os
import time
import math
import hashlib
import hmac
import urllib.request

TOOL_SCHEMA = {
    "name": "update_asset",
    "description": "Update an asset or debt with new values. Requires write permission API key. "
    "Common use case: updating current value of an asset. Supports updating name, "
    "value, cost, and description. Use --confirm flag to execute (not implemented here, "
    "add confirm=True to actually update).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "item_id": {"type": "string", "description": "Asset or debt ID to update"},
            "value": {"type": "number", "description": "New value amount"},
            "name": {"type": "string", "description": "New name (optional)"},
            "cost": {"type": "number", "description": "New cost basis (optional)"},
            "description": {"type": "string", "description": "New description (optional)"},
            "confirm": {
                "type": "boolean",
                "default": false,
                "description": "Set to true to actually execute the update",
            },
        },
        "required": ["item_id", "confirm"],
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


def execute(
    item_id: str,
    value: float = None,
    name: str = None,
    cost: float = None,
    description: str = None,
    confirm: bool = False,
) -> str:
    """
    Update an asset

    Args:
        item_id: Asset/debt ID
        value: New value
        name: New name
        cost: New cost
        description: New description
        confirm: Must be True to execute

    Returns:
        更新结果
    """
    body = {}
    if value is not None:
        body["value"] = value
    if name is not None:
        body["name"] = name
    if cost is not None:
        body["cost"] = cost
    if description is not None:
        body["description"] = description

    if not body:
        return "Error: Nothing to update. Use --value, --name, --cost, or --description."

    if not confirm:
        return f"Preview: Would update item {item_id} with:\n{json.dumps(body, indent=2)}\n\nSet confirm=true to execute."

    result = make_request(f"/api/v3/data/item/{item_id}", method="POST", body=body)

    if "error" in result:
        return f"Error: {result['error']}"

    return f"Successfully updated item {item_id}:\n{json.dumps(result, indent=2)}"


if __name__ == "__main__":
    print(execute("asset-123", value=5000, confirm=False))

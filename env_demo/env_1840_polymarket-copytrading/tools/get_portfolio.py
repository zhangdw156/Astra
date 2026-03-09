"""
Get Portfolio Tool - 获取投资组合信息

获取用户的 Simmer 投资组合余额信息。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_portfolio",
    "description": "Get portfolio balance information including USDC balance and $SIM paper trading balance. "
    "This shows available funds for copytrading.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "venue": {
                "type": "string",
                "default": "polymarket",
                "description": "Trading venue: 'polymarket' for real USDC, 'simmer' for $SIM paper trading",
            }
        },
    },
}

SIMMER_API_BASE = os.environ.get("SIMMER_API_BASE", "http://localhost:8001")
SIMMER_API_KEY = os.environ.get("SIMMER_API_KEY", "mock-api-key")


def execute(venue: str = "polymarket") -> str:
    """
    获取投资组合信息

    Args:
        venue: 交易场所

    Returns:
        格式化的余额信息
    """
    output = f"## 💰 Portfolio: {venue}\n\n"

    try:
        url = f"{SIMMER_API_BASE}/api/sdk/portfolio?venue={venue}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {SIMMER_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        balance = data.get("balance", 0)
        available = data.get("available", 0)
        positions_value = data.get("positions_value", 0)

        output += f"**Balance:** ${balance:.2f}\n"
        output += f"**Available:** ${available:.2f}\n"
        output += f"**Positions Value:** ${positions_value:.2f}\n"

        if venue == "simmer":
            output += f"\n**Note:** $SIM is paper trading currency.\n"
            output += f"Each market has independent $10K $SIM balance.\n"
        else:
            output += f"\n**Note:** Requires USDC in Polymarket wallet for real trading.\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

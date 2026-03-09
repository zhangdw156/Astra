"""
Get Wallet Positions Tool - 获取指定钱包的头寸

获取指定 Polymarket 钱包的当前头寸。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_wallet_positions",
    "description": "Get current positions held by a specific Polymarket wallet address. "
    "Use this to check what positions a whale or trader holds before copying them.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet": {
                "type": "string",
                "description": "Wallet address to check (e.g., '0x123...abcd')",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of positions to return",
            },
        },
        "required": ["wallet"],
    },
}

SIMMER_API_BASE = os.environ.get("SIMMER_API_BASE", "http://localhost:8001")
SIMMER_API_KEY = os.environ.get("SIMMER_API_KEY", "mock-api-key")


def execute(wallet: str, limit: int = 20) -> str:
    """
    获取指定钱包的头寸

    Args:
        wallet: 钱包地址
        limit: 最大返回数量

    Returns:
        格式化的头寸列表
    """
    output = f"## Wallet Positions: `{wallet}`\n\n"

    try:
        encoded_wallet = urllib.parse.quote(wallet)
        url = f"{SIMMER_API_BASE}/api/sdk/wallet/positions?wallet={encoded_wallet}&limit={limit}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {SIMMER_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        positions = data.get("positions", [])

        if not positions:
            output += "No positions found for this wallet.\n"
            return output

        output += f"**Total Positions:** {len(positions)}\n\n"

        for i, pos in enumerate(positions, 1):
            question = pos.get("question", "Unknown")[:50]
            shares_yes = pos.get("shares_yes", 0)
            shares_no = pos.get("shares_no", 0)
            value = pos.get("current_value", 0)
            pnl = pos.get("pnl", 0)

            if shares_yes > shares_no:
                side = f"{shares_yes:.1f} YES"
            else:
                side = f"{shares_no:.1f} NO"

            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

            output += f"{i}. **{question}**\n"
            output += f"   - Position: {side}\n"
            output += f"   - Value: ${value:.2f} | P&L: {pnl_str}\n\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("0x1234567890abcdef1234567890abcdef12345678"))

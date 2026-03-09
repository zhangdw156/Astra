"""
Get My Positions Tool - 获取用户当前头寸

获取当前用户的 copytrading 头寸。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_my_positions",
    "description": "Get current copytrading positions for the user. "
    "This shows what positions the user holds from copytrading activity, "
    "including P&L for each position.",
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
    获取用户的当前头寸

    Args:
        venue: 交易场所

    Returns:
        格式化的头寸列表
    """
    output = f"## 📊 Your Copytrading Positions ({venue})\n\n"

    try:
        url = f"{SIMMER_API_BASE}/api/sdk/positions?venue={venue}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {SIMMER_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        positions = data.get("positions", [])

        if not positions:
            output += "No positions found.\n"
            output += "\n**To start copytrading:**\n"
            output += "1. Configure target wallets\n"
            output += "2. Run copytrade command with a wallet address\n"
            return output

        total_value = 0
        total_pnl = 0

        for i, pos in enumerate(positions, 1):
            question = pos.get("question", "Unknown market")[:50]
            shares_yes = pos.get("shares_yes", 0)
            shares_no = pos.get("shares_no", 0)
            value = pos.get("current_value", 0)
            pnl = pos.get("pnl", 0)
            cost_basis = pos.get("cost_basis", 1)

            total_value += value
            total_pnl += pnl

            if shares_yes > shares_no:
                side = f"{shares_yes:.1f} YES"
            else:
                side = f"{shares_no:.1f} NO"

            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0
            pnl_pct_str = f"+{pnl_pct:.1f}%" if pnl_pct >= 0 else f"{pnl_pct:.1f}%"

            output += f"{i}. **{question}**\n"
            output += f"   - Position: {side}\n"
            output += f"   - Value: ${value:.2f} | P&L: {pnl_str} ({pnl_pct_str})\n\n"

        output += f"**Summary:**\n"
        output += f"- Total Value: ${total_value:.2f}\n"
        output += f"- Total P&L: {'+' if total_pnl >= 0 else ''}${total_pnl:.2f}\n"
        output += f"- Positions: {len(positions)}\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Get Wallet Positions - 获取 Polymarket 钱包当前持仓

获取指定钱包在 Polymarket 上的当前持仓情况。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_wallet_positions",
    "description": "Get current positions for a Polymarket wallet. "
    "Returns all active positions with profit/loss information.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "Polymarket wallet address (0x... format)",
            }
        },
        "required": ["wallet_address"],
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(wallet_address: str) -> str:
    """
    获取钱包当前持仓

    Args:
        wallet_address: Polymarket 钱包地址

    Returns:
        格式化的持仓信息
    """
    try:
        encoded_address = urllib.parse.quote(wallet_address)
        url = f"{POLYMARKET_API_BASE}/wallet/{encoded_address}/positions"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("positions"):
            return f"No active positions for wallet {wallet_address}"

        output = f"## Active Positions for {wallet_address[:10]}...{wallet_address[-6:]}\n\n"

        total_pnl = 0
        for pos in data["positions"]:
            pnl = pos.get("pnl", 0)
            total_pnl += pnl
            pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

            output += f"**{pos.get('market_question', 'N/A')}**\n"
            output += f"- Shares: {pos.get('shares', 0)} | Side: {pos.get('side', 'N/A').upper()}\n"
            output += f"- Entry: ${pos.get('entry_price', 0):.2f} | Current: ${pos.get('current_price', 0):.2f}\n"
            output += f"- P&L: {pnl_str}\n\n"

        output += f"**Total P&L: {'+' if total_pnl >= 0 else ''}${total_pnl:.2f}**"

        return output

    except Exception as e:
        return f"Error fetching wallet positions: {str(e)}"


if __name__ == "__main__":
    print(execute("0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f"))

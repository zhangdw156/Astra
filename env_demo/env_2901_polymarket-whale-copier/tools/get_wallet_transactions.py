"""
Get Wallet Transactions - 获取 Polymarket 钱包交易历史

获取指定钱包在 Polymarket 上的交易历史记录。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_wallet_transactions",
    "description": "Get transaction history for a Polymarket wallet. "
    "Returns all trades made by the wallet including buy/sell orders, amounts, and prices.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet_address": {
                "type": "string",
                "description": "Polymarket wallet address (0x... format)",
            },
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of transactions to return",
            },
        },
        "required": ["wallet_address"],
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(wallet_address: str, limit: int = 20) -> str:
    """
    获取钱包交易历史

    Args:
        wallet_address: Polymarket 钱包地址
        limit: 返回的最大交易数量

    Returns:
        格式化的交易历史
    """
    try:
        encoded_address = urllib.parse.quote(wallet_address)
        url = f"{POLYMARKET_API_BASE}/wallet/{encoded_address}/transactions?limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if not data.get("transactions"):
            return f"No transactions found for wallet {wallet_address}"

        output = f"## Transactions for {wallet_address[:10]}...{wallet_address[-6:]}\n\n"

        for tx in data["transactions"]:
            action = "BUY" if tx.get("side") == "buy" else "SELL"
            output += f"**{action}** {tx.get('amount', 0)} shares @ ${tx.get('price', 0):.2f}\n"
            output += f"- Market: {tx.get('market_question', 'N/A')}\n"
            output += f"- Time: {tx.get('timestamp', 'N/A')}\n"
            output += f"- Total: ${tx.get('total', 0):.2f}\n\n"

        return output

    except Exception as e:
        return f"Error fetching wallet transactions: {str(e)}"


if __name__ == "__main__":
    print(execute("0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f"))

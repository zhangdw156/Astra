"""
Simulate Copy Trade - 模拟复制交易

模拟将巨鲸钱包的交易复制到用户账户的效果。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "simulate_copy_trade",
    "description": "Simulate copying a whale's trade to your account. "
    "Shows what the copy would look like based on your settings.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "whale_address": {"type": "string", "description": "Whale wallet address to copy"},
            "trade_id": {
                "type": "string",
                "description": "Specific trade ID to copy (optional, defaults to latest)",
            },
            "copy_percent": {
                "type": "integer",
                "default": 10,
                "description": "Percentage of whale's position to copy (1-100)",
            },
            "min_trade_usd": {
                "type": "number",
                "default": 5,
                "description": "Minimum trade amount in USD",
            },
            "max_trade_usd": {
                "type": "number",
                "default": 50,
                "description": "Maximum trade amount in USD",
            },
        },
        "required": ["whale_address"],
    },
}

POLYMARKET_API_BASE = os.environ.get("POLYMARKET_API_BASE", "http://localhost:8001")


def execute(
    whale_address: str,
    trade_id: str = None,
    copy_percent: int = 10,
    min_trade_usd: float = 5,
    max_trade_usd: float = 50,
) -> str:
    """
    模拟复制交易

    Args:
        whale_address: 巨鲸钱包地址
        trade_id: 要复制的交易 ID（可选，默认最新）
        copy_percent: 复制百分比
        min_trade_usd: 最小交易金额
        max_trade_usd: 最大交易金额

    Returns:
        格式化的模拟结果
    """
    try:
        encoded_address = urllib.parse.quote(whale_address)

        if trade_id:
            url = f"{POLYMARKET_API_BASE}/wallet/{encoded_address}/transactions/{trade_id}"
        else:
            url = f"{POLYMARKET_API_BASE}/wallet/{encoded_address}/transactions?limit=1"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if trade_id:
            tx = data.get("transaction", {})
        else:
            txs = data.get("transactions", [])
            if not txs:
                return "No transactions found for this wallet"
            tx = txs[0]

        whale_shares = tx.get("amount", 0)
        whale_price = tx.get("price", 0)
        whale_total = tx.get("total", 0)
        side = tx.get("side", "buy").upper()
        market_question = tx.get("market_question", "Unknown Market")

        copy_shares = int(whale_shares * copy_percent / 100)
        copy_total = copy_shares * whale_price

        if copy_total < min_trade_usd:
            return f"Trade skipped: Copy amount ${copy_total:.2f} is below minimum ${min_trade_usd}"

        if copy_total > max_trade_usd:
            copy_shares = int(max_trade_usd / whale_price)
            copy_total = copy_shares * whale_price

        output = f"## Simulate Copy Trade\n\n"
        output += f"**Target Whale:** {whale_address[:10]}...{whale_address[-6:]}\n"
        output += f"**Market:** {market_question}\n\n"

        output += "### Whale's Original Trade\n"
        output += f"- Action: **{side}** {whale_shares} shares @ ${whale_price:.2f}\n"
        output += f"- Total: ${whale_total:.2f}\n\n"

        output += "### Your Copy (simulation)\n"
        output += f"- Action: **{side}** {copy_shares} shares @ ${whale_price:.2f}\n"
        output += f"- Total: ${copy_total:.2f}\n"
        output += f"- Copy %: {copy_percent}%\n\n"

        output += "### Risk Settings Applied\n"
        output += f"- Min Trade: ${min_trade_usd}\n"
        output += f"- Max Trade: ${max_trade_usd}\n\n"

        output += "*Note: This is a simulation only. No actual trade was placed.*"

        return output

    except Exception as e:
        return f"Error simulating copy trade: {str(e)}"


if __name__ == "__main__":
    print(execute("0x4ffe49ba4a860d71b609f71d5f5c54a6609f609f"))

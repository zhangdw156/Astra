"""
Execute Buyback Tool - 执行代币回购

执行自动回购操作，将收取的费用兑换为$BANKR代币。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "execute_buyback",
    "description": "Execute buyback of collected fees to $BANKR token via Uniswap. "
    "This is typically run automatically when fees accumulate to $100+, "
    "but can be triggered manually by admin. Converts USDC/ETH fees to $BANKR "
    "to create buy pressure and support the token.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "Amount in USDC to swap for $BANKR"},
            "admin_key": {"type": "string", "description": "Admin key for authorization"},
        },
        "required": ["amount", "admin_key"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(amount: float, admin_key: str) -> str:
    """
    执行代币回购

    Args:
        amount: USDC 数量
        admin_key: 管理员密钥

    Returns:
        回购结果
    """
    try:
        import urllib.parse

        params = urllib.parse.urlencode({"amount": amount, "admin_key": admin_key})
        url = f"{PORTFOLIO_API_BASE}/api/buyback/execute?{params}"

        with urllib.request.urlopen(url, timeout=60) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = "## Buyback Executed ✅\n\n"
        output += f"**Amount Swapped**: ${data.get('amountUsdc', 0):,.2f} USDC\n"
        output += f"**$BANKR Received**: {data.get('bankrBought', 0):,.0f} tokens\n"
        output += f"**Price**: ${data.get('price', 0):.6f} per $BANKR\n"
        output += f"**Transaction**: `{data.get('txHash', 'N/A')}`\n\n"

        output += "### Buyback Stats\n\n"
        stats = data.get("stats", {})
        output += f"- **Total Revenue**: ${stats.get('totalRevenue', 0):,.2f}\n"
        output += f"- **Total BANKR Bought**: {stats.get('totalBankrBought', 0):,.0f}\n"
        output += f"- **Average Price**: ${stats.get('avgPrice', 0):.6f}\n"
        output += f"- **Buy Pressure**: ${stats.get('buyPressure', 0):,.2f}\n"

        return output

    except urllib.error.HTTPError as e:
        return f"Error: Admin key invalid or insufficient fees. HTTP {e.code}"
    except Exception as e:
        return f"Error executing buyback: {str(e)}"


if __name__ == "__main__":
    print(execute(100, "secret"))

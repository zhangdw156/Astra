"""
Verify Payment Tool - 验证支付

验证用户的支付交易或$BANKR代币持有情况，确认是否有权限使用分析服务。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "verify_payment",
    "description": "Verify payment transaction or check $BANKR token holding for service access. "
    "Users get free access if they hold >=1000 $BANKR, or can pay $5 per scan. "
    "Use this to verify user eligibility before running analysis.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet": {"type": "string", "description": "User wallet address to verify"},
            "tx_hash": {
                "type": "string",
                "description": "Payment transaction hash (optional if checking BANKR holding)",
            },
        },
        "required": ["wallet"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(wallet: str, tx_hash: str = None) -> str:
    """
    验证支付或代币持有

    Args:
        wallet: 用户钱包地址
        tx_hash: 支付交易哈希 (可选)

    Returns:
        验证结果
    """
    try:
        if tx_hash:
            url = f"{PORTFOLIO_API_BASE}/api/payment/verify?wallet={wallet}&tx_hash={tx_hash}"
        else:
            url = f"{PORTFOLIO_API_BASE}/api/payment/verify?wallet={wallet}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = "## Payment Verification\n\n"

        if data.get("hasAccess"):
            output += "✅ **Access Granted**\n\n"
        else:
            output += "❌ **Access Denied**\n\n"

        if data.get("bankrBalance") is not None:
            output += f"**$BANKR Balance**: {data['bankrBalance']:,.0f} tokens\n"
            if data["bankrBalance"] >= 1000:
                output += "✓ Qualifies for free access (>= 1000 $BANKR)\n"
            else:
                output += "✗ Does not qualify (need >= 1000 $BANKR)\n"
            output += "\n"

        if data.get("payment"):
            payment = data["payment"]
            output += "**Payment Details:**\n"
            output += f"- Amount: ${payment.get('amount', 0):.2f}\n"
            output += f"- Timestamp: {payment.get('timestamp', 'N/A')}\n"
            output += f"- Status: {'✅ Verified' if payment.get('valid') else '❌ Invalid'}\n"
            output += "\n"

        if data.get("subscription"):
            sub = data["subscription"]
            output += "**Subscription:**\n"
            output += f"- Status: {sub.get('status', 'N/A')}\n"
            if sub.get("expires"):
                output += f"- Expires: {sub['expires']}\n"
            output += "\n"

        output += "**Access Methods:**\n"
        output += "- Hold >= 1000 $BANKR (free unlimited access)\n"
        output += "- Pay $5 per scan (24hr validity)\n"
        output += "- Subscribe $20/month (unlimited access)\n"

        return output

    except Exception as e:
        return f"Error verifying payment: {str(e)}"


if __name__ == "__main__":
    print(execute("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"))

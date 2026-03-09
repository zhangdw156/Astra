"""
Sell Whale Exits Tool - 跟随卖出

当鲸鱼平仓时自动卖出对应的头寸。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "sell_whale_exits",
    "description": "Sell positions when the whales you are copying have exited those markets. "
    "This compares your copytrading positions to the target wallets and sells any positions "
    "that whales no longer hold. Useful for risk management.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallets": {
                "type": "string",
                "description": "Comma-separated wallet addresses to check for exits",
            },
            "live": {
                "type": "boolean",
                "default": False,
                "description": "Execute real trades (default: dry-run)",
            },
        },
        "required": ["wallets"],
    },
}

SIMMER_API_BASE = os.environ.get("SIMMER_API_BASE", "http://localhost:8001")
SIMMER_API_KEY = os.environ.get("SIMMER_API_KEY", "mock-api-key")


def execute(wallets: str, live: bool = False) -> str:
    """
    执行跟随卖出

    Args:
        wallets: 逗号分隔的钱包地址
        live: 是否执行真实交易

    Returns:
        格式化的结果
    """
    wallet_list = [w.strip() for w in wallets.split(",") if w.strip()]

    output = f"## 🔻 Whale Exits Check\n\n"
    output += f"**Checking exits from {len(wallet_list)} wallets:**\n"
    for w in wallet_list:
        output += f"- `{w}`\n"
    output += f"\n**Mode:** {'LIVE' if live else 'DRY RUN'}\n\n"

    try:
        url = f"{SIMMER_API_BASE}/api/sdk/copytrading/whale-exits"

        data = {
            "wallets": wallet_list,
            "dry_run": not live,
        }

        json_data = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Authorization": f"Bearer {SIMMER_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode())

        exits_detected = result.get("whale_exits_detected", 0)
        output += f"**Exits detected:** {exits_detected}\n"

        trades = result.get("trades", [])
        if trades:
            output += f"\n**Sell trades:**\n\n"
            for t in trades:
                action = t.get("action", "?").upper()
                side = t.get("side", "?").upper()
                shares = t.get("shares", 0)
                price = t.get("estimated_price", 0)
                cost = t.get("estimated_cost", 0)
                title = t.get("market_title", "Unknown")[:40]
                success = t.get("success", False)

                status = "✅" if success else "⏸️"
                output += f"{status} {action} {shares:.1f} {side} @ ${price:.3f} (${cost:.2f})\n"
                output += f"   - {title}...\n\n"
        else:
            output += "\nNo exits detected - all positions still held by whales.\n"

        output += f"\n**Summary:** {result.get('summary', 'Complete')}\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("0x1234567890abcdef1234567890abcdef12345678"))

"""
Copytrade Wallets Tool - 执行 Copytrading

镜像指定钱包的 Polymarket 头寸。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "copytrade_wallets",
    "description": "Run copytrading to mirror positions from specific Polymarket wallets. "
    "This executes the Simmer SDK copytrading logic which fetches whale positions, "
    "applies size-weighted aggregation, detects conflicts, and calculates trades. "
    "Use this when user wants to copytrade specific wallets.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallets": {
                "type": "string",
                "description": "Comma-separated wallet addresses to copytrade (e.g., '0x123...,0x456...')",
            },
            "top_n": {
                "type": "integer",
                "description": "Number of top positions to mirror (default: auto based on balance)",
            },
            "max_usd": {
                "type": "number",
                "default": 50,
                "description": "Max USD per position (default: $50)",
            },
            "live": {
                "type": "boolean",
                "default": False,
                "description": "Execute real trades (default: dry-run)",
            },
            "rebalance": {
                "type": "boolean",
                "default": False,
                "description": "Full rebalance mode: buy AND sell (default: buy-only)",
            },
        },
        "required": ["wallets"],
    },
}

SIMMER_API_BASE = os.environ.get("SIMMER_API_BASE", "http://localhost:8001")
SIMMER_API_KEY = os.environ.get("SIMMER_API_KEY", "mock-api-key")


def execute(
    wallets: str,
    top_n: int = None,
    max_usd: float = 50.0,
    live: bool = False,
    rebalance: bool = False,
) -> str:
    """
    执行 copytrading

    Args:
        wallets: 逗号分隔的钱包地址
        top_n: Top N 头寸数量
        max_usd: 每仓位最大 USD
        live: 是否执行真实交易
        rebalance: 是否全量调仓

    Returns:
        格式化的 copytrading 结果
    """
    wallet_list = [w.strip() for w in wallets.split(",") if w.strip()]

    output = f"## 🐋 Copytrading Execution\n\n"
    output += f"**Target Wallets:** {len(wallet_list)}\n"
    for w in wallet_list:
        output += f"- `{w}`\n"
    output += f"\n**Settings:**\n"
    output += f"- Top N: {top_n if top_n else 'auto'}\n"
    output += f"- Max per position: ${max_usd}\n"
    output += f"- Mode: {'LIVE' if live else 'DRY RUN'}\n"
    output += f"- Rebalance: {'Yes (buy + sell)' if rebalance else 'No (buy-only)'}\n\n"

    try:
        url = f"{SIMMER_API_BASE}/api/sdk/copytrading/execute"

        data = {
            "wallets": wallet_list,
            "max_usd_per_position": max_usd,
            "dry_run": not live,
            "buy_only": not rebalance,
        }

        if top_n is not None:
            data["top_n"] = top_n

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

        output += f"**Execution Results:**\n\n"
        output += f"- Wallets analyzed: {result.get('wallets_analyzed', 0)}\n"
        output += f"- Positions found: {result.get('positions_found', 0)}\n"
        output += f"- Conflicts skipped: {result.get('conflicts_skipped', 0)}\n"

        trades = result.get("trades", [])
        if trades:
            output += f"\n**Trades:**\n\n"
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
            output += f"\nNo trades needed.\n"

        output += f"\n**Summary:** {result.get('summary', 'Complete')}\n"

    except Exception as e:
        output += f"**Error:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("0x1234567890abcdef1234567890abcdef12345678"))

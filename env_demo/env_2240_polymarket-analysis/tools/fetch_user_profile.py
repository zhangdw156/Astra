"""
Fetch User Profile Tool - Get Polymarket user positions and trades

Fetches a user's positions, trades, and P&L from Polymarket.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "fetch_user_profile",
    "description": "Fetch Polymarket user profile with positions, trades, and P&L. "
    "Provide a wallet address to get their trading activity.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet_address": {"type": "string", "description": "Wallet address (0x...)"},
            "include_trades": {
                "type": "boolean",
                "default": False,
                "description": "Include trade history",
            },
            "include_pnl": {
                "type": "boolean",
                "default": False,
                "description": "Include P&L history",
            },
        },
        "required": ["wallet_address"],
    },
}

DATA_API_BASE = os.environ.get("DATA_API_BASE", "http://localhost:8002")


def fetch_api(endpoint: str) -> dict | list | None:
    """Fetch data from Data API."""
    url = f"{DATA_API_BASE}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PolymarketProfile/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def format_positions(positions: list) -> str:
    """Format positions for display."""
    if not positions:
        return "No open positions."

    lines = []
    total_pnl = 0

    for p in positions:
        market = p.get("title", p.get("market", "Unknown"))[:40]
        outcome = p.get("outcome", "?")
        size = float(p.get("size", 0))
        avg_price = float(p.get("avgPrice", 0))
        cur_price = float(p.get("curPrice", p.get("currentPrice", 0)))
        pnl = float(p.get("pnl", (cur_price - avg_price) * size))
        total_pnl += pnl

        lines.append(f"- **{market}**")
        lines.append(f"  - Side: {outcome}, Shares: {size:.1f}")
        lines.append(f"  - Entry: ${avg_price:.3f}, Current: ${cur_price:.3f}")
        lines.append(f"  - P&L: ${pnl:+.2f}\n")

    lines.append(f"**Total P&L:** ${total_pnl:+.2f}")
    return "\n".join(lines)


def execute(wallet_address: str, include_trades: bool = False, include_pnl: bool = False) -> str:
    """Fetch Polymarket user profile."""
    output = f"## Polymarket Profile\n\n"

    wallet = wallet_address.lower()
    if not wallet.startswith("0x"):
        return output + "Error: Invalid wallet address. Must start with 0x.\n"

    output += f"**Wallet:** {wallet[:10]}...{wallet[-6:]}\n\n"

    positions = fetch_api(f"/positions?user={wallet}")

    if positions is None:
        output += "Error: Could not fetch positions. Check the wallet address.\n"
        return output

    output += f"### Positions\n"
    output += format_positions(positions if isinstance(positions, list) else []) + "\n"

    if include_trades:
        trades = fetch_api(f"/trades?user={wallet}")
        if trades and isinstance(trades, list):
            output += f"\n### Recent Trades ({len(trades)} found)\n"
            for t in trades[:5]:
                output += f"- {t.get('side', '?')} {t.get('size', 0)} @ ${t.get('price', 0):.3f}\n"

    if include_pnl:
        pnl = fetch_api(f"/profit-loss?user={wallet}")
        if pnl and isinstance(pnl, list):
            output += f"\n### P&L History ({len(pnl)} records)\n"
            total = sum(float(x.get("pnl", 0)) for x in pnl)
            output += f"**Net P&L:** ${total:+.2f}\n"

    return output


if __name__ == "__main__":
    print(execute("0x7845bc5e15bc9c41be5ac0725e68a16ec02b51b5"))

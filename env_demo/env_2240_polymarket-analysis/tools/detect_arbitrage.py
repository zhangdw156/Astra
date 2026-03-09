"""
Detect Arbitrage Tool - Find pair cost arbitrage opportunities

Scans active markets for pair cost < $1.00 arbitrage opportunities.
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "detect_arbitrage",
    "description": "Scan Polymarket markets for pair cost arbitrage opportunities. "
    "Finds markets where YES + NO < $1.00.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "threshold": {
                "type": "number",
                "default": 0.98,
                "description": "Maximum pair cost threshold (default 0.98)",
            },
            "limit": {"type": "integer", "default": 20, "description": "Maximum markets to scan"},
        },
        "required": [],
    },
}

GAMMA_API_BASE = os.environ.get("GAMMA_API_BASE", "http://localhost:8001")


def fetch_api(endpoint: str) -> dict | list | None:
    """Fetch data from Gamma API."""
    url = f"{GAMMA_API_BASE}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ArbitrageScanner/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def execute(threshold: float = 0.98, limit: int = 20) -> str:
    """Detect arbitrage opportunities in Polymarket markets."""
    output = f"## Polymarket Arbitrage Scanner\n\n"
    output += f"**Threshold:** Pair cost < ${threshold:.2f}\n\n"

    data = fetch_api(f"/markets?active=true&closed=false&limit={limit}")

    if not data or not isinstance(data, list):
        return output + "Error: Could not fetch markets.\n"

    opportunities = []

    for market in data:
        prices = market.get("outcomePrices", [])
        if isinstance(prices, str):
            try:
                prices = json.loads(prices) if prices.startswith("[") else []
            except:
                prices = []

        if len(prices) >= 2:
            yes_price = float(prices[0])
            no_price = float(prices[1])
            pair_cost = yes_price + no_price

            if pair_cost < threshold:
                opportunities.append(
                    {
                        "question": market.get("question", "Unknown"),
                        "slug": market.get("slug", ""),
                        "yes_price": yes_price,
                        "no_price": no_price,
                        "pair_cost": pair_cost,
                        "profit_pct": (1 - pair_cost) * 100,
                        "volume": float(market.get("volume", 0) or 0),
                    }
                )

    if opportunities:
        output += f"### Found {len(opportunities)} Opportunities\n\n"

        for opp in sorted(opportunities, key=lambda x: x["profit_pct"], reverse=True):
            output += f"**{opp['question'][:60]}**\n"
            output += f"- YES: ${opp['yes_price']:.3f} | NO: ${opp['no_price']:.3f}\n"
            output += f"- Pair Cost: ${opp['pair_cost']:.4f} | Profit: {opp['profit_pct']:.2f}%\n"
            output += f"- Volume: ${opp['volume']:,.0f}\n\n"
    else:
        output += "No arbitrage opportunities found with current threshold.\n"

    return output


if __name__ == "__main__":
    print(execute())

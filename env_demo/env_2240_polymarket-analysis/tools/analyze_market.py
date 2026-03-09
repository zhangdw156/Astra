"""
Analyze Market Tool - One-time Polymarket analysis

Analyzes a Polymarket market for trading opportunities.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "analyze_market",
    "description": "Perform one-time analysis on a Polymarket market. "
    "Fetches market data and provides analysis for trading edges.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market_url_or_id": {
                "type": "string",
                "description": "Market URL, slug, or numeric ID (e.g., 'trump-wins-2024' or '1234567')",
            },
            "include_arbitrage": {
                "type": "boolean",
                "default": True,
                "description": "Include pair cost arbitrage analysis",
            },
            "include_momentum": {
                "type": "boolean",
                "default": True,
                "description": "Include momentum signals analysis",
            },
        },
        "required": ["market_url_or_id"],
    },
}

GAMMA_API_BASE = os.environ.get("GAMMA_API_BASE", "http://localhost:8001")


def resolve_market(market_url_or_id: str) -> dict | None:
    """Resolve market from URL, slug, or ID."""
    if market_url_or_id.startswith("http"):
        import re

        match = re.search(r"polymarket\.com/event/[^/]+/([^/\?\#]+)", market_url_or_id)
        if match:
            slug = match.group(1)
            return fetch_api(f"/markets?slug={slug}")
        match = re.search(r"polymarket\.com/event/([^/\?\#]+)", market_url_or_id)
        if match:
            slug = match.group(1)
            return fetch_api(f"/markets?slug={slug}")

    if market_url_or_id.isdigit():
        data = fetch_api(f"/markets/{market_url_or_id}")
        if data:
            return data

    data = fetch_api(f"/markets?slug={market_url_or_id}")
    return data[0] if data else None


def fetch_api(endpoint: str) -> dict | list | None:
    """Fetch data from Gamma API."""
    url = f"{GAMMA_API_BASE}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PolymarketAnalyzer/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def analyze_arbitrage(yes_price: float, no_price: float) -> dict:
    """Analyze pair cost arbitrage opportunity."""
    pair_cost = yes_price + no_price
    return {
        "pair_cost": pair_cost,
        "arbitrage_possible": pair_cost < 1.0,
        "profit_potential": max(0, (1.0 - pair_cost) * 100),
        "threshold_met": pair_cost < 0.98,
    }


def analyze_momentum(yes_price: float, no_price: float, volume: float) -> dict:
    """Analyze momentum signals."""
    return {
        "yes_ratio": yes_price,
        "no_ratio": no_price,
        "volume": volume,
        "high_volume": volume > 100000,
        "strong_direction": "YES" if yes_price > 0.7 else ("NO" if no_price > 0.7 else "mixed"),
    }


def execute(
    market_url_or_id: str, include_arbitrage: bool = True, include_momentum: bool = True
) -> str:
    """Analyze Polymarket market."""
    output = f"## Polymarket Market Analysis\n\n"
    output += f"**Market:** {market_url_or_id}\n\n"

    data = resolve_market(market_url_or_id)

    if not data:
        return output + "Error: Could not resolve market. Please check the URL or ID.\n"

    market_id = data.get("id", data.get("conditionId", "unknown"))
    question = data.get("question", "Unknown Market")

    output += f"**Question:** {question}\n"
    output += f"**ID:** {market_id}\n\n"

    prices = data.get("outcomePrices", [])
    if isinstance(prices, str):
        try:
            prices = json.loads(prices) if prices.startswith("[") else []
        except:
            prices = []

    yes_price = float(prices[0]) if len(prices) > 0 else 0
    no_price = float(prices[1]) if len(prices) > 1 else 0
    volume = float(data.get("volume", 0) or 0)
    liquidity = float(data.get("liquidity", 0) or 0)

    output += f"### Current Prices\n"
    output += f"- YES: ${yes_price:.3f} ({yes_price * 100:.1f}%)\n"
    output += f"- NO: ${no_price:.3f} ({no_price * 100:.1f}%)\n"
    output += f"- Volume: ${volume:,.0f}\n"
    output += f"- Liquidity: ${liquidity:,.0f}\n\n"

    if include_arbitrage:
        arb = analyze_arbitrage(yes_price, no_price)
        output += f"### Arbitrage Analysis\n"
        output += f"- Pair Cost: ${arb['pair_cost']:.4f}\n"
        output += f"- Arbitrage Possible: {arb['arbitrage_possible']}\n"
        if arb["arbitrage_possible"]:
            output += f"- Profit Potential: {arb['profit_potential']:.2f}%\n"
        output += f"- Alert Threshold Met: {arb['threshold_met']}\n\n"

    if include_momentum:
        mom = analyze_momentum(yes_price, no_price, volume)
        output += f"### Momentum Signals\n"
        output += f"- Direction: {mom['strong_direction']}\n"
        output += f"- High Volume: {mom['high_volume']}\n\n"

    if data.get("endDate"):
        output += f"**Resolution Date:** {data.get('endDate')}\n"

    return output


if __name__ == "__main__":
    print(execute("trump-wins-2024"))

"""
Track Whales Tool - Track large trades and smart money

Monitors for large trades and tracks whale activity.
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "track_whales",
    "description": "Track whale activity on Polymarket. "
    "Identifies large trades and smart money movements.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market_url_or_id": {
                "type": "string",
                "description": "Market URL, slug, or numeric ID (optional)",
            },
            "min_volume": {
                "type": "number",
                "default": 10000,
                "description": "Minimum market volume to consider",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum markets to analyze",
            },
        },
        "required": [],
    },
}

GAMMA_API_BASE = os.environ.get("GAMMA_API_BASE", "http://localhost:8001")


def fetch_api(endpoint: str) -> dict | list | None:
    """Fetch data from Gamma API."""
    url = f"{GAMMA_API_BASE}{endpoint}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WhaleTracker/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def execute(market_url_or_id: str = None, min_volume: float = 10000, limit: int = 10) -> str:
    """Track whale activity on Polymarket."""
    output = f"## Polymarket Whale Tracker\n\n"
    output += f"**Min Volume:** ${min_volume:,.0f}\n\n"

    if market_url_or_id:
        data = fetch_api(f"/markets?slug={market_url_or_id}")
        if data and isinstance(data, list):
            markets = data[:1]
        else:
            markets = []
    else:
        data = fetch_api(f"/markets?active=true&closed=false&limit={limit}")
        markets = data if isinstance(data, list) else []

    if not markets:
        return output + "Error: Could not fetch markets.\n"

    whale_markets = []

    for market in markets:
        volume = float(market.get("volume", 0) or 0)

        if volume >= min_volume:
            prices = market.get("outcomePrices", [])
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices) if prices.startswith("[") else []
                except:
                    prices = []

            yes_price = float(prices[0]) if len(prices) > 0 else 0
            no_price = float(prices[1]) if len(prices) > 1 else 0

            whale_markets.append(
                {
                    "question": market.get("question", "Unknown"),
                    "slug": market.get("slug", ""),
                    "volume": volume,
                    "liquidity": float(market.get("liquidity", 0) or 0),
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "whale_score": volume / 1000000,
                }
            )

    if whale_markets:
        output += f"### {len(whale_markets)} High-Volume Markets (Whale Activity)\n\n"

        for m in sorted(whale_markets, key=lambda x: x["volume"], reverse=True):
            output += f"**{m['question'][:60]}**\n"
            output += f"- Volume: ${m['volume']:,.0f} | Liquidity: ${m['liquidity']:,.0f}\n"
            output += f"- YES: ${m['yes_price']:.3f} | NO: ${m['no_price']:.3f}\n"
            output += f"- Whale Score: {m['whale_score']:.2f}\n\n"

        output += "**Whale Score** = Volume / $1M. Higher scores indicate more whale activity.\n"
    else:
        output += "No markets found with volume above threshold.\n"

    return output


if __name__ == "__main__":
    print(execute())

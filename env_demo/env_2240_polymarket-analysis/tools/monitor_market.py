"""
Monitor Market Tool - Monitor Polymarket for alerts

Monitors a market for price changes, whale trades, and arbitrage opportunities.
"""

import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TOOL_SCHEMA = {
    "name": "monitor_market",
    "description": "Monitor a Polymarket market for alerts including price changes, "
    "large trades, and arbitrage opportunities.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market_url_or_id": {
                "type": "string",
                "description": "Market URL, slug, or numeric ID",
            },
            "threshold_price": {
                "type": "number",
                "default": 0.05,
                "description": "Price change threshold (default 5%)",
            },
            "threshold_whale": {
                "type": "number",
                "default": 5000,
                "description": "Whale trade threshold in USD (default $5000)",
            },
            "threshold_arb": {
                "type": "number",
                "default": 0.98,
                "description": "Arbitrage pair cost threshold (default $0.98)",
            },
        },
        "required": ["market_url_or_id"],
    },
}

GAMMA_API_BASE = os.environ.get("GAMMA_API_BASE", "http://localhost:8001")


def resolve_market(market_url_or_id: str) -> dict | None:
    """Resolve market from URL, slug, or ID."""
    if market_url_or_id.startswith("http"):
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
        req = urllib.request.Request(url, headers={"User-Agent": "PolymarketMonitor/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def detect_alerts(current: dict, thresholds: dict) -> list[dict]:
    """Detect alerts based on current market data."""
    alerts = []

    yes_price = current.get("yes_price", 0)
    no_price = current.get("no_price", 0)
    volume = current.get("volume", 0)

    # Arbitrage opportunity
    pair_cost = yes_price + no_price
    if pair_cost < thresholds["arb"] and pair_cost > 0:
        profit_pct = (1 - pair_cost) * 100
        alerts.append(
            {
                "type": "arbitrage",
                "message": f"Pair cost ${pair_cost:.4f} < ${thresholds['arb']:.2f} - potential {profit_pct:.2f}% arb",
            }
        )

    # High volume alert
    if volume > thresholds["whale"]:
        alerts.append(
            {
                "type": "whale_trade",
                "message": f"High volume: ${volume:,.0f} (threshold: ${thresholds['whale']:,.0f})",
            }
        )

    # Strong directional signal
    if yes_price > 0.8:
        alerts.append(
            {"type": "strong_signal", "message": f"Strong YES sentiment: {yes_price * 100:.0f}%"}
        )
    elif no_price > 0.8:
        alerts.append(
            {"type": "strong_signal", "message": f"Strong NO sentiment: {no_price * 100:.0f}%"}
        )

    return alerts


def execute(
    market_url_or_id: str,
    threshold_price: float = 0.05,
    threshold_whale: float = 5000,
    threshold_arb: float = 0.98,
) -> str:
    """Monitor Polymarket market for alerts."""
    output = f"## Polymarket Market Monitor\n\n"
    output += f"**Market:** {market_url_or_id}\n\n"

    data = resolve_market(market_url_or_id)

    if not data:
        return output + "Error: Could not resolve market.\n"

    market_id = str(data.get("id", data.get("conditionId", "unknown")))
    question = data.get("question", "Unknown")

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

    current = {
        "market_id": market_id,
        "name": question,
        "yes_price": yes_price,
        "no_price": no_price,
        "pair_cost": yes_price + no_price,
        "volume": volume,
        "liquidity": liquidity,
    }

    output += f"### Market Data\n"
    output += f"**Question:** {question}\n"
    output += f"- YES: ${yes_price:.3f} | NO: ${no_price:.3f} | Pair: ${current['pair_cost']:.3f}\n"
    output += f"- Volume: ${volume:,.0f} | Liquidity: ${liquidity:,.0f}\n\n"

    thresholds = {"price": threshold_price, "whale": threshold_whale, "arb": threshold_arb}

    alerts = detect_alerts(current, thresholds)

    if alerts:
        output += "### Alerts\n"
        for alert in alerts:
            output += f"- **[{alert['type'].upper()}]** {alert['message']}\n"
    else:
        output += "### Alerts\nNo alerts triggered with current thresholds.\n"

    output += f"\n**Thresholds:** Price={threshold_price * 100:.0f}%, Whale=${threshold_whale:,.0f}, Arb=${threshold_arb:.2f}\n"

    return output


if __name__ == "__main__":
    print(execute("trump-wins-2024"))

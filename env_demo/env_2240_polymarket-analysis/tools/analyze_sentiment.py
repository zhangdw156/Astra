"""
Analyze Sentiment Tool - Analyze market sentiment

Provides sentiment analysis for Polymarket markets.
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "analyze_sentiment",
    "description": "Analyze sentiment for Polymarket markets. "
    "Provides directional sentiment based on price levels.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "market_url_or_id": {
                "type": "string",
                "description": "Market URL, slug, or numeric ID",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Number of markets to analyze if no specific market",
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
        req = urllib.request.Request(url, headers={"User-Agent": "SentimentAnalyzer/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_sentiment(yes_price: float) -> str:
    """Get sentiment label based on price."""
    if yes_price >= 0.8:
        return "Strong YES"
    elif yes_price >= 0.6:
        return "Moderate YES"
    elif yes_price >= 0.4:
        return "Neutral/Mixed"
    elif yes_price >= 0.2:
        return "Moderate NO"
    else:
        return "Strong NO"


def execute(market_url_or_id: str = None, limit: int = 10) -> str:
    """Analyze market sentiment."""
    output = f"## Polymarket Sentiment Analysis\n\n"

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

    sentiments = {
        "Strong YES": [],
        "Moderate YES": [],
        "Neutral/Mixed": [],
        "Moderate NO": [],
        "Strong NO": [],
    }

    for market in markets:
        prices = market.get("outcomePrices", [])
        if isinstance(prices, str):
            try:
                prices = json.loads(prices) if prices.startswith("[") else []
            except:
                prices = []

        yes_price = float(prices[0]) if len(prices) > 0 else 0.5
        sentiment = get_sentiment(yes_price)

        sentiments[sentiment].append(
            {
                "question": market.get("question", "Unknown")[:50],
                "yes_price": yes_price,
                "volume": float(market.get("volume", 0) or 0),
            }
        )

    for sentiment_label, markets_list in sentiments.items():
        if markets_list:
            output += f"### {sentiment_label} ({len(markets_list)})\n"
            for m in markets_list[:3]:
                output += f"- {m['question']}: YES ${m['yes_price']:.3f} (${m['volume']:,.0f})\n"
            output += "\n"

    return output


if __name__ == "__main__":
    print(execute())

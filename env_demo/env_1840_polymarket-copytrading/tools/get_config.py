"""
Get Config Tool - 获取当前配置

获取 copytrading 的当前配置（钱包、Top N、最大仓位等）。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_config",
    "description": "Get current copytrading configuration including target wallets, Top N setting, "
    "max position size, and other settings.",
    "inputSchema": {"type": "object", "properties": {}},
}

SIMMER_API_BASE = os.environ.get("SIMMER_API_BASE", "http://localhost:8001")
SIMMER_API_KEY = os.environ.get("SIMMER_API_KEY", "mock-api-key")


def execute() -> str:
    """
    获取当前配置

    Returns:
        格式化的配置信息
    """
    output = "## ⚙️ Copytrading Configuration\n\n"

    try:
        url = f"{SIMMER_API_BASE}/api/sdk/copytrading/config"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {SIMMER_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        wallets = data.get("wallets", [])
        output += f"**Target Wallets:** {len(wallets)}\n"
        if wallets:
            for w in wallets:
                output += f"- `{w[:10]}...{w[-6:]}`\n"
        else:
            output += "- (none configured)\n"

        top_n = data.get("top_n")
        output += f"\n**Top N:** {top_n if top_n else 'auto (based on balance)'}\n"

        max_usd = data.get("max_usd", 50)
        output += f"**Max per position:** ${max_usd}\n"

        max_trades = data.get("max_trades", 10)
        output += f"**Max trades per run:** {max_trades}\n"

        venue = data.get("venue", "polymarket")
        output += f"**Venue:** {venue}\n"

    except Exception as e:
        output += f"**Note:** Using default configuration\n\n"
        output += f"- Target Wallets: (set via SIMMER_COPYTRADING_WALLETS env var)\n"
        output += f"- Top N: auto (based on balance)\n"
        output += f"- Max per position: $50\n"
        output += f"- Max trades: 10\n\n"
        output += f"**Error fetching config:** {str(e)}\n"

    output += "\n**To change settings:**\n"
    output += "- Set `SIMMER_COPYTRADING_WALLETS` env var with comma-separated wallet addresses\n"
    output += "- Set `SIMMER_COPYTRADING_TOP_N` for fixed Top N\n"
    output += "- Set `SIMMER_COPYTRADING_MAX_USD` for max position size\n"

    return output


if __name__ == "__main__":
    print(execute())

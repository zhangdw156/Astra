"""
Get Copy Settings - 获取复制交易设置

获取当前配置的复制交易参数。
"""

import json
import os

TOOL_SCHEMA = {
    "name": "get_copy_settings",
    "description": "Get current copy trading configuration settings. "
    "Shows target wallet, copy percentage, and risk controls.",
    "inputSchema": {"type": "object", "properties": {}},
}

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/app/config.json")


def execute() -> str:
    """
    获取当前复制交易设置

    Returns:
        格式化的设置信息
    """
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
        else:
            config = {
                "target_wallet": None,
                "copy_percent": 10,
                "min_trade_usd": 5,
                "max_trade_usd": 50,
                "buy_only": True,
                "check_interval_sec": 60,
                "dry_run": True,
            }

        output = "## Copy Trading Settings\n\n"

        target = config.get("target_wallet")
        if target:
            output += f"**Target Wallet:** `{target}`\n"
        else:
            output += "**Target Wallet:** Not configured\n"

        output += f"**Copy Percent:** {config.get('copy_percent', 10)}%\n"
        output += f"**Min Trade:** ${config.get('min_trade_usd', 5)}\n"
        output += f"**Max Trade:** ${config.get('max_trade_usd', 50)}\n"
        output += f"**Buy Only:** {'Yes' if config.get('buy_only', True) else 'No'}\n"
        output += f"**Check Interval:** {config.get('check_interval_sec', 60)} seconds\n"
        output += f"**Dry Run:** {'Yes' if config.get('dry_run', True) else 'No'}\n"

        return output

    except Exception as e:
        return f"Error loading settings: {str(e)}"


if __name__ == "__main__":
    print(execute())

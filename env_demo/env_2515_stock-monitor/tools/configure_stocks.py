"""
Configure Stocks Tool - 配置监控股票

添加或更新股票配置。
"""

import json
import os

TOOL_SCHEMA = {
    "name": "configure_stocks",
    "description": "Add or update stock configuration for monitoring. Include stock name, symbol, base price, and currency.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Stock name (e.g., '贵州茅台', '腾讯控股', 'Apple')",
            },
            "symbol": {
                "type": "string",
                "description": "Yahoo Finance symbol (e.g., 600519.SS, 0700.HK, AAPL)",
            },
            "base_price": {
                "type": "number",
                "description": "Base/reference price for alert calculation",
            },
            "currency": {"type": "string", "description": "Currency symbol (e.g., ¥, HK$, $)"},
        },
        "required": ["name", "symbol", "base_price", "currency"],
    },
}

CONFIG_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_config.json")


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"stocks": {}}


def save_config(config):
    """保存配置"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def execute(name: str, symbol: str, base_price: float, currency: str) -> str:
    """
    添加或更新股票配置

    Args:
        name: 股票名称
        symbol: 股票代码
        base_price: 基准价
        currency: 货币符号

    Returns:
        操作结果
    """
    config = load_config()

    if "stocks" not in config:
        config["stocks"] = {}

    config["stocks"][name] = {"symbol": symbol, "base_price": base_price, "currency": currency}

    save_config(config)

    return f"已添加/更新股票: {name} ({symbol}), 基准价: {currency}{base_price:.2f}"


if __name__ == "__main__":
    print(execute("Apple", "AAPL", 180.0, "$"))

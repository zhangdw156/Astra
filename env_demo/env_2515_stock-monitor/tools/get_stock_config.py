"""
Get Stock Config Tool - 获取当前股票配置

查看已配置的股票列表。
"""

import json
import os

TOOL_SCHEMA = {
    "name": "get_stock_config",
    "description": "Get the current list of configured stocks for monitoring.",
    "inputSchema": {"type": "object", "properties": {}},
}

CONFIG_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_config.json")


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {"stocks": {}}


def execute() -> str:
    """
    获取当前股票配置

    Returns:
        格式化的配置信息
    """
    config = load_config()
    stocks = config.get("stocks", {})

    if not stocks:
        return "当前没有配置任何股票。使用 configure_stocks 工具添加股票。"

    output = "## 当前监控股票配置\n\n"
    output += "| 名称 | 代码 | 基准价 | 货币 |\n"
    output += "|------|------|--------|------|\n"

    for name, cfg in stocks.items():
        output += f"| {name} | {cfg['symbol']} | {cfg['base_price']:.2f} | {cfg['currency']} |\n"

    return output


if __name__ == "__main__":
    print(execute())

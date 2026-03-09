"""
Reset Alerts Tool - 重置预警状态

重置指定股票或所有股票的预警状态。
"""

import json
import os

TOOL_SCHEMA = {
    "name": "reset_alerts",
    "description": "Reset alert status for stocks. Can reset a specific stock or all stocks.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "stock_name": {
                "type": "string",
                "description": "Stock name to reset (leave empty to reset all)",
            }
        },
    },
}

STATE_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_alert.json")


def load_state():
    """加载状态"""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    """保存状态"""
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def execute(stock_name: str = None) -> str:
    """
    重置预警状态

    Args:
        stock_name: 股票名称，为空则重置所有

    Returns:
        操作结果
    """
    state = load_state()

    if not state:
        return "没有预警状态需要重置"

    if stock_name:
        if stock_name in state:
            state[stock_name]["alerted"] = False
            state[stock_name]["alert_date"] = None
            state[stock_name]["last_alert_price"] = None
            save_state(state)
            return f"已重置 {stock_name} 的预警状态"
        else:
            return f"未找到股票: {stock_name}"
    else:
        for name in state:
            state[name]["alerted"] = False
            state[name]["alert_date"] = None
            state[name]["last_alert_price"] = None
        save_state(state)
        return "已重置所有股票的预警状态"


if __name__ == "__main__":
    print(execute())

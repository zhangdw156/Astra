"""
Get Alert Status Tool - 获取预警状态

查看各股票的预警状态和价格信息。
"""

import json
import os
from datetime import datetime

TOOL_SCHEMA = {
    "name": "get_alert_status",
    "description": "Get the current alert status for all configured stocks, including whether alerts have been triggered and last check prices.",
    "inputSchema": {"type": "object", "properties": {}},
}

STATE_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_alert.json")


def load_state():
    """加载状态"""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    return {}


def execute() -> str:
    """
    获取预警状态

    Returns:
        格式化的状态信息
    """
    state = load_state()

    if not state:
        return "暂无预警状态记录，请先运行 monitor_stocks 进行监控。"

    output = "## 股票预警状态\n\n"

    for name, stock_state in state.items():
        output += f"### {name}\n"
        output += f"- 当前价格: {stock_state.get('current_price', 'N/A')}\n"
        output += f"- 基准价: {stock_state.get('base_price', 'N/A')}\n"
        output += f"- 已预警: {'是' if stock_state.get('alerted') else '否'}\n"
        output += f"- 预警日期: {stock_state.get('alert_date', 'N/A')}\n"
        output += f"- 最后检查: {stock_state.get('last_check', 'N/A')}\n\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Monitor Stocks Tool - 监控所有配置的股票价格

检查所有已配置的股票，当价格波动超过阈值时发送预警。
首次预警: 涨跌超过 2%
续警: 同一天内，再波动超过 1%
"""

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "monitor_stocks",
    "description": "Monitor all configured stocks and check for price alerts. Uses 2% threshold for first alert and 1% for follow-up alerts within the same day.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "config_path": {
                "type": "string",
                "description": "Path to stock config file (default: ~/.openclaw/workspace/memory/stocks_config.json)",
            }
        },
    },
}

STOCK_API_BASE = os.environ.get("STOCK_API_BASE", "http://localhost:8003")

CONFIG_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_config.json")
STATE_PATH = os.path.expanduser("~/.openclaw/workspace/memory/stocks_alert.json")

ALERT_THRESHOLD_2PCT = 0.02
ALERT_THRESHOLD_1PCT = 0.01


def get_price_from_api(symbol):
    """从 API 获取股票价格"""
    url = f"{STOCK_API_BASE}/stock/price/{symbol}"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data.get("price")
    except Exception:
        return None


def load_config(config_path):
    """加载股票配置"""
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {
        "stocks": {
            "贵州茅台": {"symbol": "600519.SS", "base_price": 1600.0, "currency": "¥"},
            "腾讯控股": {"symbol": "0700.HK", "base_price": 512.0, "currency": "HK$"},
            "拼多多": {"symbol": "PDD", "base_price": 120.0, "currency": "$"},
        }
    }


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


def check_stock(name, config):
    """检查单只股票"""
    symbol = config["symbol"]
    base = config["base_price"]
    currency = config["currency"]

    price = get_price_from_api(symbol)
    if not price:
        return None

    state = load_state()
    if name not in state:
        state[name] = {
            "alerted": False,
            "alert_date": None,
            "base_price": base,
            "last_alert_price": None,
        }

    stock_state = state[name]
    alerted = stock_state.get("alerted", False)
    alert_date = stock_state.get("alert_date")
    base_price = stock_state.get("base_price", base)
    last_alert_price = stock_state.get("last_alert_price")

    today = datetime.now().strftime("%Y-%m-%d")
    change_pct = (price - base_price) / base_price * 100

    message = None

    if alert_date != today:
        stock_state["alerted"] = False
        stock_state["alert_date"] = None
        stock_state["last_alert_price"] = None
        stock_state["base_price"] = price

    if not stock_state["alerted"]:
        alert_2pct_up = base_price * (1 + ALERT_THRESHOLD_2PCT)
        alert_2pct_down = base_price * (1 - ALERT_THRESHOLD_2PCT)

        if price >= alert_2pct_up:
            message = f"🚀 {name}预警：现价 {currency}{price:.2f}，涨{change_pct:.2f}% 首次超 2%"
            stock_state["alerted"] = True
            stock_state["alert_date"] = today
            stock_state["last_alert_price"] = price
        elif price <= alert_2pct_down:
            message = (
                f"📉 {name}预警：现价 {currency}{price:.2f}，跌{abs(change_pct):.2f}% 首次超 2%"
            )
            stock_state["alerted"] = True
            stock_state["alert_date"] = today
            stock_state["last_alert_price"] = price
    else:
        if last_alert_price:
            change_from_last = (price - last_alert_price) / last_alert_price * 100

            if abs(change_from_last) >= ALERT_THRESHOLD_1PCT * 100:
                if change_from_last > 0:
                    message = f"📈 {name}续警：现价 {currency}{price:.2f}，较上次涨{change_from_last:.2f}%"
                else:
                    message = f"📉 {name}续警：现价 {currency}{price:.2f}，较上次跌{abs(change_from_last):.2f}%"
                stock_state["last_alert_price"] = price

    stock_state["current_price"] = price
    stock_state["last_check"] = today
    save_state(state)

    return message


def execute(config_path: str = None) -> str:
    """
    监控所有配置的股票

    Args:
        config_path: 配置文件路径

    Returns:
        预警信息，如果没有预警则返回空
    """
    cfg_path = config_path or CONFIG_PATH
    config = load_config(cfg_path)
    stocks = config.get("stocks", {})

    if not stocks:
        return "请先配置股票列表"

    results = []
    for name, cfg in stocks.items():
        result = check_stock(name, cfg)
        if result:
            results.append(result)

    if not results:
        return "没有触发预警"

    return "\n".join(results)


if __name__ == "__main__":
    print(execute())

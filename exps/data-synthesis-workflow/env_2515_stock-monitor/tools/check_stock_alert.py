"""
Check Stock Alert Tool - 检查股票是否触发预警

根据设置的基准价和阈值检查股票是否触发预警。
首次预警：涨跌超过 2%
续警：同一天内，再波动超过 1%
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime

TOOL_SCHEMA = {
    "name": "check_stock_alert",
    "description": "Check if a stock triggers an alert based on price threshold. "
    "First alert triggers at +/-2% change from base price. "
    "Follow-up alert triggers at +/-1% from last alert price within same day.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock symbol (e.g., 600519.SS, 0700.HK, AAPL)",
            },
            "base_price": {
                "type": "number",
                "description": "Base/reference price to compare against",
            },
            "currency": {
                "type": "string",
                "default": "$",
                "description": "Currency symbol ($, HK$, ¥)",
            },
            "name": {"type": "string", "description": "Stock name for display (optional)"},
        },
        "required": ["symbol", "base_price"],
    },
}

YAHOO_FINANCE_BASE = os.environ.get("YAHOO_FINANCE_BASE", "http://localhost:8003")

ALERT_THRESHOLD_2PCT = 0.02
ALERT_THRESHOLD_1PCT = 0.01


def get_state_path():
    return os.path.expanduser("~/.openclaw/workspace/memory/stock_alert_state.json")


def load_state():
    state_path = get_state_path()
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            return json.load(f)
    return {}


def save_state(state):
    state_path = get_state_path()
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def execute(symbol: str, base_price: float, currency: str = "$", name: str = None) -> str:
    """
    检查股票是否触发预警

    Args:
        symbol: 股票代码
        base_price: 基准价
        currency: 货币符号
        name: 股票名称（可选）

    Returns:
        预警检查结果
    """
    stock_name = name or symbol
    use_mock = os.environ.get("USE_MOCK", "true").lower() == "true"

    if use_mock:
        current_price = get_price_mock(symbol)
    else:
        current_price = get_price_real(symbol)

    if current_price is None:
        return f"❌ 无法获取 {stock_name} ({symbol}) 的实时价格"

    return check_alert(symbol, stock_name, base_price, current_price, currency)


def get_price_mock(symbol: str):
    """从 Mock API 获取价格"""
    try:
        url = f"{YAHOO_FINANCE_BASE}/quote/{urllib.parse.quote(symbol)}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())
        if data.get("error"):
            return None
        return data.get("price")
    except Exception:
        return None


def get_price_real(symbol: str):
    """从真实 Yahoo Finance API 获取价格"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=5m&range=1d"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        if "chart" in data and "result" in data["chart"] and data["chart"]["result"]:
            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            price = meta.get("regularMarketPrice")
            if price:
                return float(price)
        return None
    except Exception:
        return None


def check_alert(
    symbol: str, stock_name: str, base_price: float, current_price: float, currency: str
) -> str:
    """检查是否触发预警"""
    state = load_state()

    if symbol not in state:
        state[symbol] = {
            "alerted": False,
            "alert_date": None,
            "base_price": base_price,
            "last_alert_price": None,
        }

    stock_state = state[symbol]
    alerted = stock_state.get("alerted", False)
    alert_date = stock_state.get("alert_date")
    last_alert_price = stock_state.get("last_alert_price")

    today = datetime.now().strftime("%Y-%m-%d")
    change_pct = (current_price - base_price) / base_price * 100

    message = None

    # 新的一天，重置
    if alert_date != today:
        stock_state["alerted"] = False
        stock_state["alert_date"] = None
        stock_state["last_alert_price"] = None
        stock_state["base_price"] = current_price

    # 首次预警：涨跌超 2%
    if not stock_state["alerted"]:
        alert_2pct_up = base_price * (1 + ALERT_THRESHOLD_2PCT)
        alert_2pct_down = base_price * (1 - ALERT_THRESHOLD_2PCT)

        if current_price >= alert_2pct_up:
            message = f"🚀 {stock_name}预警：现价 {currency}{current_price:.2f}，涨{change_pct:.2f}% 首次超 2%"
            stock_state["alerted"] = True
            stock_state["alert_date"] = today
            stock_state["last_alert_price"] = current_price
        elif current_price <= alert_2pct_down:
            message = f"📉 {stock_name}预警：现价 {currency}{current_price:.2f}，跌{abs(change_pct):.2f}% 首次超 2%"
            stock_state["alerted"] = True
            stock_state["alert_date"] = today
            stock_state["last_alert_price"] = current_price
    else:
        # 续警：相对上次 alert 价格再波动超 1%
        if last_alert_price:
            change_from_last = (current_price - last_alert_price) / last_alert_price * 100

            if abs(change_from_last) >= ALERT_THRESHOLD_1PCT * 100:
                if change_from_last > 0:
                    message = f"📈 {stock_name}续警：现价 {currency}{current_price:.2f}，较上次涨{change_from_last:.2f}%"
                else:
                    message = f"📉 {stock_name}续警：现价 {currency}{current_price:.2f}，较上次跌{abs(change_from_last):.2f}%"
                stock_state["last_alert_price"] = current_price

    stock_state["current_price"] = current_price
    stock_state["last_check"] = today
    save_state(state)

    output = f"## {stock_name} ({symbol})\n\n"
    output += f"- **当前价格**: {currency}{current_price:.2f}\n"
    output += f"- **基准价**: {currency}{base_price:.2f}\n"
    output += f"- **涨跌**: {change_pct:+.2f}%\n"

    if stock_state["alerted"]:
        output += f"- **状态**: ⚠️ 已预警\n"
    else:
        output += f"- **状态**: ✅ 正常\n"

    if message:
        output += f"\n**{message}**\n"

    return output


if __name__ == "__main__":
    print(execute("AAPL", 180.0, "$", "Apple"))
    print(execute("600519.SS", 1600.0, "¥", "贵州茅台"))

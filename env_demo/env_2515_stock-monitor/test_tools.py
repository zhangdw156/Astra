#!/usr/bin/env python3
"""
测试工具脚本 - 验证工具可以正常调用 Mock API
"""

import os
import sys

os.environ["STOCK_API_BASE"] = "http://localhost:8003"

sys.path.insert(0, os.path.dirname(__file__))


def test_get_stock_price():
    """测试 get_stock_price 工具"""
    from tools.get_stock_price import execute

    result = execute("AAPL")
    print("=" * 50)
    print("TEST: get_stock_price")
    print("=" * 50)
    print(result)
    print()


def test_configure_stocks():
    """测试 configure_stocks 工具"""
    from tools.configure_stocks import execute

    result = execute("Apple", "AAPL", 180.0, "$")
    print("=" * 50)
    print("TEST: configure_stocks")
    print("=" * 50)
    print(result)
    print()


def test_get_stock_config():
    """测试 get_stock_config 工具"""
    from tools.get_stock_config import execute

    result = execute()
    print("=" * 50)
    print("TEST: get_stock_config")
    print("=" * 50)
    print(result)
    print()


def test_monitor_stocks():
    """测试 monitor_stocks 工具"""
    from tools.monitor_stocks import execute

    result = execute()
    print("=" * 50)
    print("TEST: monitor_stocks")
    print("=" * 50)
    print(result)
    print()


def test_get_alert_status():
    """测试 get_alert_status 工具"""
    from tools.get_alert_status import execute

    result = execute()
    print("=" * 50)
    print("TEST: get_alert_status")
    print("=" * 50)
    print(result)
    print()


def test_reset_alerts():
    """测试 reset_alerts 工具"""
    from tools.reset_alerts import execute

    result = execute()
    print("=" * 50)
    print("TEST: reset_alerts")
    print("=" * 50)
    print(result)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Running tool tests...")
    print("Note: Make sure Mock API is running on port 8003")
    print("=" * 50 + "\n")

    test_configure_stocks()
    test_get_stock_config()
    test_get_stock_price()
    test_monitor_stocks()
    test_get_alert_status()
    test_reset_alerts()

    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

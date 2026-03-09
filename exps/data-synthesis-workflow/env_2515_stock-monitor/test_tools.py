#!/usr/bin/env python3
"""
Test script for stock-monitor tools
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.get_stock_price import execute as get_stock_price
from tools.get_multiple_stock_prices import execute as get_multiple_stock_prices
from tools.check_stock_alert import execute as check_stock_alert


def test_get_stock_price():
    print("=" * 50)
    print("Testing get_stock_price")
    print("=" * 50)
    result = get_stock_price("AAPL", "Apple")
    print(result)
    print()


def test_get_multiple_stock_prices():
    print("=" * 50)
    print("Testing get_multiple_stock_prices")
    print("=" * 50)
    result = get_multiple_stock_prices("AAPL:Apple,600519.SS:贵州茅台,0700.HK:腾讯控股")
    print(result)
    print()


def test_check_stock_alert():
    print("=" * 50)
    print("Testing check_stock_alert")
    print("=" * 50)
    result = check_stock_alert("AAPL", 180.0, "$", "Apple")
    print(result)
    print()


if __name__ == "__main__":
    os.environ["USE_MOCK"] = "true"
    os.environ["YAHOO_FINANCE_BASE"] = "http://localhost:8003"

    test_get_stock_price()
    test_get_multiple_stock_prices()
    test_check_stock_alert()

    print("All tests completed!")

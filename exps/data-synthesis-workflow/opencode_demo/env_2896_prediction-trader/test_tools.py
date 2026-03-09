#!/usr/bin/env python3
"""
测试工具脚本 - 验证工具可以正常调用 Mock API
"""

import os
import sys

# 设置环境变量
os.environ["UNIFAI_API_BASE"] = "http://localhost:8001"
os.environ["KALSHI_API_BASE"] = "http://localhost:8002"
os.environ["UNIFAI_AGENT_API_KEY"] = "mock-api-key"

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))


def test_kalshi_fed():
    """测试 kalshi_fed 工具"""
    from tools.kalshi_fed import execute
    result = execute(limit=3)
    print("=" * 50)
    print("TEST: kalshi_fed")
    print("=" * 50)
    print(result)
    print()


def test_kalshi_economics():
    """测试 kalshi_economics 工具"""
    from tools.kalshi_economics import execute
    result = execute(limit=3)
    print("=" * 50)
    print("TEST: kalshi_economics")
    print("=" * 50)
    print(result)
    print()


def test_polymarket_trending():
    """测试 polymarket_trending 工具"""
    from tools.polymarket_trending import execute
    result = execute()
    print("=" * 50)
    print("TEST: polymarket_trending")
    print("=" * 50)
    print(result)
    print()


def test_polymarket_crypto():
    """测试 polymarket_crypto 工具"""
    from tools.polymarket_crypto import execute
    result = execute()
    print("=" * 50)
    print("TEST: polymarket_crypto")
    print("=" * 50)
    print(result)
    print()


def test_compare_markets():
    """测试 compare_markets 工具"""
    from tools.compare_markets import execute
    result = execute(topic="bitcoin", limit=3)
    print("=" * 50)
    print("TEST: compare_markets")
    print("=" * 50)
    print(result)
    print()


def test_trending():
    """测试 trending 工具"""
    from tools.trending import execute
    result = execute(limit=3)
    print("=" * 50)
    print("TEST: trending")
    print("=" * 50)
    print(result)
    print()


def test_analyze_topic():
    """测试 analyze_topic 工具"""
    from tools.analyze_topic import execute
    result = execute(topic="bitcoin")
    print("=" * 50)
    print("TEST: analyze_topic")
    print("=" * 50)
    print(result)
    print()


def test_kalshi_search():
    """测试 kalshi_search 工具"""
    from tools.kalshi_search import execute
    result = execute(query="bitcoin", limit=3)
    print("=" * 50)
    print("TEST: kalshi_search")
    print("=" * 50)
    print(result)
    print()


def test_polymarket_search():
    """测试 polymarket_search 工具"""
    from tools.polymarket_search import execute
    result = execute(query="bitcoin")
    print("=" * 50)
    print("TEST: polymarket_search")
    print("=" * 50)
    print(result)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Running tool tests...")
    print("Note: Make sure Mock APIs are running on ports 8001 and 8002")
    print("=" * 50 + "\n")

    # 测试所有工具
    test_kalshi_fed()
    test_kalshi_economics()
    test_kalshi_search()
    test_polymarket_trending()
    test_polymarket_crypto()
    test_polymarket_search()
    test_compare_markets()
    test_trending()
    test_analyze_topic()

    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

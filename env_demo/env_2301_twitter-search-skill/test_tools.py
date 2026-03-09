#!/usr/bin/env python3
"""
测试工具脚本 - 验证工具可以正常调用 Mock API
"""

import os
import sys

os.environ["TWITTER_API_BASE"] = "http://localhost:8003"
os.environ["TWITTER_API_KEY"] = "mock-api-key"

sys.path.insert(0, os.path.dirname(__file__))


def test_twitter_search():
    """测试 twitter_search 工具"""
    from tools.twitter_search import execute

    print("=" * 50)
    print("TEST: twitter_search")
    print("=" * 50)

    result = execute(query="AI", max_results=10, query_type="Top")
    print(result)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Running tool tests...")
    print("Note: Make sure Mock API is running on port 8003")
    print("=" * 50 + "\n")

    test_twitter_search()

    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

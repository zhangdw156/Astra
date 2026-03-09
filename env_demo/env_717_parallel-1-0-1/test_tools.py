#!/usr/bin/env python3
"""
Tool smoke tests - 验证所有工具可正常执行
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tools.search import execute as search_execute


def test_search():
    print("Testing search...")
    result = search_execute("Who is the CEO of Anthropic?", max_results=3)
    print(result)
    assert "Search ID:" in result
    print("✓ search passed\n")


def main():
    print("=" * 40)
    print("Running tool smoke tests...")
    print("=" * 40 + "\n")

    test_search()

    print("=" * 40)
    print("All tests passed!")
    print("=" * 40)


if __name__ == "__main__":
    main()

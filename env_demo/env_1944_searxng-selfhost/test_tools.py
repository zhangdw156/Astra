#!/usr/bin/env python3
"""
Test script to verify all tools work correctly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.search import execute as search_execute


def test_search():
    """Test search tool"""
    print("\n=== Testing search tool ===")
    result = search_execute("python tutorial", count=5)
    print(result)
    assert len(result) > 0, "Search should return results"
    print("✓ search tool works\n")


def main():
    print("Testing SearXNG MCP tools...")

    try:
        test_search()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

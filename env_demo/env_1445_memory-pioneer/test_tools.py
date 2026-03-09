#!/usr/bin/env python3
"""
Test script to run each tool's execute() function for smoke testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    collect_memory_stats,
    run_memory_assessment,
    run_metric_tests,
    get_test_queries,
)


def main():
    print("=" * 50)
    print("Memory Pioneer Tools - Smoke Test")
    print("=" * 50)

    tools = [
        ("get_test_queries", get_test_queries.execute),
        ("run_metric_tests", run_metric_tests.execute),
        ("collect_memory_stats", collect_memory_stats.execute),
        ("run_memory_assessment", run_memory_assessment.execute),
    ]

    for name, func in tools:
        print(f"\n--- Testing: {name} ---")
        try:
            if name == "get_test_queries":
                result = func(limit=5)
            elif name == "run_metric_tests":
                result = func()
            elif name == "collect_memory_stats":
                result = func(days=7)
            elif name == "run_memory_assessment":
                result = func(num_queries=3)
            else:
                result = func()

            if len(result) > 500:
                print(result[:500] + "...")
            else:
                print(result)
            print(f"✅ {name} passed")
        except Exception as e:
            print(f"❌ {name} failed: {e}")

    print("\n" + "=" * 50)
    print("Smoke test complete")
    print("=" * 50)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Tool smoke tests - run each tool to verify it works
"""

import sys
import os

os.environ.setdefault("UNIFUNCS_API_BASE", "http://localhost:8001")
os.environ.setdefault("UNIFUNCS_API_KEY", "mock-api-key")

sys.path.insert(0, os.path.dirname(__file__))

from tools.read import execute


def test_read():
    """Test read tool"""
    print("Testing read tool...")
    result = execute(url="https://example.com")
    assert result, "Result should not be empty"
    assert "Example Domain" in result or "mock" in result.lower(), (
        f"Unexpected result: {result[:100]}"
    )
    print(f"  ✓ read tool passed")
    print(f"    Result preview: {result[:150]}...")


def main():
    """Run all tests"""
    print("=" * 40)
    print("Running tool smoke tests...")
    print("=" * 40)

    try:
        test_read()
        print("=" * 40)
        print("All tests passed!")
        print("=" * 40)
        return 0
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

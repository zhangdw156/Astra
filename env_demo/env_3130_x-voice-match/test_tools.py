#!/usr/bin/env python3
"""
Test script for X Voice Match tools.
Runs each tool's execute() function for smoke testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.analyze_voice import execute as analyze_voice_exec
from tools.generate_post import execute as generate_post_exec
from tools.quick_match import execute as quick_match_exec


def test_analyze_voice():
    print("=" * 50)
    print("Testing analyze_voice...")
    print("=" * 50)
    result = analyze_voice_exec("gravyxbt_", 30)
    print(result)
    print()


def test_generate_post():
    print("=" * 50)
    print("Testing generate_post...")
    print("=" * 50)
    result = generate_post_exec("gravyxbt_", "AI agents taking over", 3, "hot-take")
    print(result)
    print()


def test_quick_match():
    print("=" * 50)
    print("Testing quick_match...")
    print("=" * 50)
    result = quick_match_exec("gravyxbt_", "bitcoin moon", 3)
    print(result)
    print()


if __name__ == "__main__":
    test_analyze_voice()
    test_generate_post()
    test_quick_match()
    print("All tests completed!")

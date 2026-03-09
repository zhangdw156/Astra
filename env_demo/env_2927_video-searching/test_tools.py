#!/usr/bin/env python3
"""
Test script for video search tools
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tools.video_search import execute as video_search
from tools.video_deterministic import execute as video_deterministic
from tools.video_trending import execute as video_trending
from tools.video_compare import execute as video_compare


def test_video_search():
    print("\n=== Testing video_search ===")
    result = video_search("AI technology")
    print(result[:500])


def test_video_deterministic():
    print("\n=== Testing video_deterministic ===")
    result = video_deterministic("bitcoin")
    print(result[:500])


def test_video_trending():
    print("\n=== Testing video_trending ===")
    result = video_trending(category="tech")
    print(result[:500])


def test_video_compare():
    print("\n=== Testing video_compare ===")
    result = video_compare("machine learning")
    print(result[:500])


if __name__ == "__main__":
    print("Testing Video Search Tools...")
    test_video_search()
    test_video_deterministic()
    test_video_trending()
    test_video_compare()
    print("\n=== All tests completed ===")

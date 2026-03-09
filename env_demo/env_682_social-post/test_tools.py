#!/usr/bin/env python3
"""
Social Post Tools Test Script

测试所有工具的基本功能。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    post_to_twitter,
    post_to_farcaster,
    post_to_both,
    reply_to_twitter,
    reply_to_farcaster,
    preview_post,
)


def test_preview_post():
    print("=" * 40)
    print("Testing preview_post...")
    result = preview_post.execute("gm! Building onchain 🦞")
    print(result)
    print()


def test_post_to_twitter():
    print("=" * 40)
    print("Testing post_to_twitter (dry_run)...")
    result = post_to_twitter.execute(text="Test tweet from MCP tool", dry_run=True)
    print(result)
    print()


def test_post_to_farcaster():
    print("=" * 40)
    print("Testing post_to_farcaster (dry_run)...")
    result = post_to_farcaster.execute(text="Test cast from MCP tool", dry_run=True)
    print(result)
    print()


def test_post_to_both():
    print("=" * 40)
    print("Testing post_to_both (dry_run)...")
    result = post_to_both.execute(text="Test cross-post from MCP tool", dry_run=True)
    print(result)
    print()


def test_reply_to_twitter():
    print("=" * 40)
    print("Testing reply_to_twitter (dry_run)...")
    result = reply_to_twitter.execute(
        tweet_id="1234567890123456789", text="Great point!", dry_run=True
    )
    print(result)
    print()


def test_reply_to_farcaster():
    print("=" * 40)
    print("Testing reply_to_farcaster (dry_run)...")
    result = reply_to_farcaster.execute(
        cast_hash="0xa1b2c3d4e5f6", text="Great insight!", dry_run=True
    )
    print(result)
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Social Post Tools - Smoke Tests")
    print("=" * 50 + "\n")

    test_preview_post()
    test_post_to_twitter()
    test_post_to_farcaster()
    test_post_to_both()
    test_reply_to_twitter()
    test_reply_to_farcaster()

    print("=" * 50)
    print("All tests completed!")
    print("=" * 50)

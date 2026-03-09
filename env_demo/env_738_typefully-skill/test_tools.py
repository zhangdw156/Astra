#!/usr/bin/env python3
"""
Test script for Typefully MCP tools
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from tools.list_drafts import execute as list_drafts
from tools.create_draft import execute as create_draft
from tools.get_draft import execute as get_draft
from tools.edit_draft import execute as edit_draft
from tools.schedule_draft import execute as schedule_draft
from tools.delete_draft import execute as delete_draft
from tools.list_social_sets import execute as list_social_sets


def test_list_social_sets():
    print("Testing list_social_sets...")
    result = list_social_sets()
    print(result)
    print("-" * 40)


def test_list_drafts():
    print("Testing list_drafts...")
    result = list_drafts()
    print(result)
    print("-" * 40)


def test_create_draft():
    print("Testing create_draft...")
    result = create_draft("Test tweet from MCP")
    print(result)
    print("-" * 40)


def test_get_draft():
    print("Testing get_draft...")
    result = get_draft("111111")
    print(result)
    print("-" * 40)


def test_edit_draft():
    print("Testing edit_draft...")
    result = edit_draft("111111", "Updated tweet text")
    print(result)
    print("-" * 40)


def test_schedule_draft():
    print("Testing schedule_draft...")
    result = schedule_draft("111111", "next-free-slot")
    print(result)
    print("-" * 40)


def test_delete_draft():
    print("Testing delete_draft...")
    result = delete_draft("444444")
    print(result)
    print("-" * 40)


if __name__ == "__main__":
    print("=" * 40)
    print("Typefully Tools Test")
    print("=" * 40)

    os.environ["TYPEFULLY_API_BASE"] = "http://localhost:8001"
    os.environ["TYPEFULLY_API_KEY"] = "mock-api-key"
    os.environ["TYPEFULLY_SOCIAL_SET_ID"] = "123456"

    test_list_social_sets()
    test_list_drafts()
    test_create_draft()
    test_get_draft()
    test_edit_draft()
    test_schedule_draft()
    test_delete_draft()

    print("All tests completed!")

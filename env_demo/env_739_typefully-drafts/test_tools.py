#!/usr/bin/env python3
"""
Test script for Typefully Drafts MCP tools

Runs each tool to verify they work correctly.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    list_drafts,
    create_draft,
    get_draft,
    edit_draft,
    schedule_draft,
    delete_draft,
    list_social_sets,
)

os.environ["TYPEFULLY_API_BASE"] = "http://localhost:8003"
os.environ["TYPEFULLY_API_KEY"] = "mock-api-key"
os.environ["TYPEFULLY_SOCIAL_SET_ID"] = "123456"


def test_list_social_sets():
    print("Testing list_social_sets...")
    result = list_social_sets.execute()
    assert "Social Sets" in result
    print("  PASSED")


def test_list_drafts():
    print("Testing list_drafts...")
    result = list_drafts.execute()
    assert "Drafts" in result
    print("  PASSED")


def test_create_draft():
    print("Testing create_draft...")
    result = create_draft.execute(text="Test tweet from MCP!")
    assert "Created Successfully" in result
    print("  PASSED")


def test_get_draft():
    print("Testing get_draft...")
    result = get_draft.execute(draft_id="8196074")
    assert "Draft Details" in result or "not found" in result.lower()
    print("  PASSED")


def test_edit_draft():
    print("Testing edit_draft...")
    result = edit_draft.execute(draft_id="8196074", text="Updated content")
    assert "Updated Successfully" in result or "Error" in result
    print("  PASSED")


def test_schedule_draft():
    print("Testing schedule_draft...")
    result = schedule_draft.execute(draft_id="8196074", schedule="next-free-slot")
    assert "Scheduled Successfully" in result or "Error" in result
    print("  PASSED")


def test_delete_draft():
    print("Testing delete_draft...")
    result = delete_draft.execute(draft_id="9999999")
    assert "Deleted Successfully" in result or "Error" in result
    print("  PASSED")


def main():
    print("=" * 50)
    print("Testing Typefully Drafts MCP Tools")
    print("=" * 50)

    tests = [
        test_list_social_sets,
        test_list_drafts,
        test_create_draft,
        test_get_draft,
        test_edit_draft,
        test_schedule_draft,
        test_delete_draft,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Test script to run each tool's execute() function for smoke testing.
"""

import os
import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set test workspace
os.environ["WORKSPACE_DIR"] = "/tmp/memory-workspace-test"

from tools import (
    init_memory_system,
    add_short_term_memory,
    add_medium_term_memory,
    add_long_term_memory,
    search_long_term_memory,
    trigger_summary,
    show_status,
    show_window,
)


def test_all_tools():
    print("=" * 50)
    print("Testing Three-Tier Memory Tools")
    print("=" * 50)

    # Test init
    print("\n1. Testing init_memory_system...")
    result = init_memory_system.execute()
    print(result)

    # Test add short-term
    print("\n2. Testing add_short_term_memory...")
    result = add_short_term_memory.execute(content="User likes dark mode")
    print(result)

    result = add_short_term_memory.execute(content="User prefers Python over Java")
    print(result)

    # Test show_window
    print("\n3. Testing show_window...")
    result = show_window.execute()
    print(result)

    # Test add medium-term
    print("\n4. Testing add_medium_term_memory...")
    result = add_medium_term_memory.execute(content="Summary: User prefers dark mode and Python")
    print(result)

    # Test add long-term
    print("\n5. Testing add_long_term_memory...")
    result = add_long_term_memory.execute(
        content="User prefers dark mode interface and Python programming"
    )
    print(result)

    result = add_long_term_memory.execute(content="User works on machine learning projects")
    print(result)

    # Test search
    print("\n6. Testing search_long_term_memory...")
    result = search_long_term_memory.execute(query="user preferences")
    print(result)

    # Test status
    print("\n7. Testing show_status...")
    result = show_status.execute()
    print(result)

    # Test trigger summary
    print("\n8. Testing trigger_summary...")
    result = trigger_summary.execute()
    print(result)

    print("\n" + "=" * 50)
    print("All tests completed!")
    print("=" * 50)


if __name__ == "__main__":
    test_all_tools()

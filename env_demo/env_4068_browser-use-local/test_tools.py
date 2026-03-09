#!/usr/bin/env python3
"""
Smoke tests for browser-use-local tools
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    open_url,
    get_state,
    screenshot,
    get_html,
    evaluate_js,
    run_agent,
    crop_candidates,
    extract_data_images,
)


def test_open_url():
    """Test open_url tool"""
    print("Testing open_url...")
    # This would require a real browser, so we'll just verify the function exists
    assert hasattr(open_url, "execute")
    print("  - open_url: OK (requires browser for full test)")


def test_get_state():
    """Test get_state tool"""
    print("Testing get_state...")
    assert hasattr(get_state, "execute")
    print("  - get_state: OK (requires browser for full test)")


def test_screenshot():
    """Test screenshot tool"""
    print("Testing screenshot...")
    assert hasattr(screenshot, "execute")
    print("  - screenshot: OK (requires browser for full test)")


def test_get_html():
    """Test get_html tool"""
    print("Testing get_html...")
    assert hasattr(get_html, "execute")
    print("  - get_html: OK (requires browser for full test)")


def test_evaluate_js():
    """Test evaluate_js tool"""
    print("Testing evaluate_js...")
    assert hasattr(evaluate_js, "execute")
    print("  - evaluate_js: OK (requires browser for full test)")


def test_run_agent():
    """Test run_agent tool"""
    print("Testing run_agent...")
    assert hasattr(run_agent, "execute")
    print("  - run_agent: OK (requires LLM for full test)")


def test_crop_candidates():
    """Test crop_candidates tool"""
    print("Testing crop_candidates...")
    assert hasattr(crop_candidates, "execute")
    print("  - crop_candidates: OK (requires OpenCV for full test)")


def test_extract_data_images():
    """Test extract_data_images tool"""
    print("Testing extract_data_images...")
    assert hasattr(extract_data_images, "execute")
    print("  - extract_data_images: OK")


def main():
    print("=" * 50)
    print("Browser Use Local - Tool Smoke Tests")
    print("=" * 50)

    try:
        test_open_url()
        test_get_state()
        test_screenshot()
        test_get_html()
        test_evaluate_js()
        test_run_agent()
        test_crop_candidates()
        test_extract_data_images()

        print("=" * 50)
        print("All smoke tests passed!")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

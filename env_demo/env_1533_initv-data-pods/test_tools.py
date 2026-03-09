#!/usr/bin/env python3
"""
Test script to run each tool's execute() function for smoke testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools import (
    create_pod,
    list_pods,
    add_note,
    query_pod,
    export_pod,
    ingest_folder,
    semantic_search,
    list_documents,
    consent_grant,
    consent_revoke,
    consent_status,
)


def test_create_pod():
    print("Testing create_pod...")
    result = create_pod.execute("test-pod", "scholar")
    print(result)
    print("OK\n")


def test_list_pods():
    print("Testing list_pods...")
    result = list_pods.execute()
    print(result)
    print("OK\n")


def test_add_note():
    print("Testing add_note...")
    result = add_note.execute("test-pod", "Test Note", "This is test content", "test, demo")
    print(result)
    print("OK\n")


def test_query_pod():
    print("Testing query_pod...")
    result = query_pod.execute("test-pod", "test")
    print(result)
    print("OK\n")


def test_list_documents():
    print("Testing list_documents...")
    result = list_documents.execute("test-pod")
    print(result)
    print("OK\n")


def test_consent_grant():
    print("Testing consent_grant...")
    result = consent_grant.execute(["test-pod"], "openclaw", 60)
    print(result)
    print("OK\n")


def test_consent_status():
    print("Testing consent_status...")
    result = consent_status.execute()
    print(result)
    print("OK\n")


if __name__ == "__main__":
    test_create_pod()
    test_list_pods()
    test_add_note()
    test_query_pod()
    test_list_documents()
    test_consent_grant()
    test_consent_status()
    print("All tests passed!")

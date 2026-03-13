from __future__ import annotations

from pathlib import Path

import json

from astra.envs.loader import load_backend_from_skill_dir


def test_claudemem_note_and_search_flows() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    added = loaded.backend.call(
        "note",
        {
            "action": "add",
            "category": "quirks",
            "title": "Python command resolution",
            "content": "Use uv run python in this worktree instead of python.",
            "tags": "tooling,python",
        },
    )
    assert added["note"]["id"] == "note_3"

    search = loaded.backend.call("search", {"query": "uv run python", "type": "note", "limit": 5})
    assert search["results"][0]["type"] == "note"

    appended = loaded.backend.call(
        "note",
        {"action": "append", "id": "note_3", "content": "This avoids command-not-found errors."},
    )
    assert "command-not-found" in appended["note"]["content"]


def test_claudemem_session_config_and_integrity_flows() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    saved = loaded.backend.call(
        "session",
        {"action": "save", "title": "Fixture batch", "branch": "feat/test", "project": "/tmp/demo"},
        conversation_context="Migrated more fixture-backed skills and verified them with pytest.",
    )
    assert saved["session"]["id"] == "session_2"
    assert saved["session"]["content"].startswith("## Summary")

    configured = loaded.backend.call("config", {"action": "set", "key": "auto_wrap_up", "value": "true"})
    assert configured["value"] == "true"

    exported = loaded.backend.call("export", {"output_file": "backup.tar.gz"})
    assert exported["archive_file"] == "backup.tar.gz"

    verify = loaded.backend.call("verify", {})
    assert verify["ok"] is True


def test_claudemem_hybrid_profile_declares_summary_as_generated_text() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == ["summary"]
    assert profile["generated_text_policy"] == "templated-summary"

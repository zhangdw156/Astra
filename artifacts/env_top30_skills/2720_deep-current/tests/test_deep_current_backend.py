from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_deep_current_backend_tracks_threads() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    created = loaded.backend.call("add", {"title": "AI chip export controls"})
    assert created["id"] == "ai-chip-export-controls"

    loaded.backend.call("note", {"id": "ai-chip", "text": "Track policy changes"})
    loaded.backend.call(
        "source",
        {"id": "ai-chip", "url": "https://example.com/report", "desc": "brief"},
    )
    digest = loaded.backend.call("digest", {})
    assert digest["threads"][0]["note_count"] == 1
    covered = loaded.backend.call("covered", {"days": 30})
    assert covered["urls"] == ["https://example.com/report"]

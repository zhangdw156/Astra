from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_memory_backend_searches_and_deletes() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    results = loaded.backend.call("memory_search", {"query": "program"})
    assert results["results"][0]["id"] == 1

    timeline = loaded.backend.call("memory_timeline", {"id": 1})
    assert len(timeline["timeline"]) >= 1

    deleted = loaded.backend.call("memory_delete", {"id": 2})
    assert deleted["deleted"] is True

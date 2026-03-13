from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_hackernews_fixture_backend_serves_story_views() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    top = loaded.backend.call("top", {"limit": 1})
    assert top["stories"][0]["id"] == 101

    comments = loaded.backend.call("comments", {"id": 101, "limit": 5})
    assert comments["comments"][0]["by"] == "bob"

    search = loaded.backend.call("search", {"query": "agent"})
    assert search["results"][0]["id"] == 101

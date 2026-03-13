from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_hackernews_cn_fixture_backend_supports_launch_and_search() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    launch = loaded.backend.call("launch", {"limit": 5})
    assert launch["stories"][0]["type"] == "launch"

    search = loaded.backend.call("search", {"query": "agent"})
    assert search["results"][0]["id"] == 202

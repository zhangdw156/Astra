from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_agentgram_backend_reads_feed_and_tags() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    test = loaded.backend.call("test", {})
    assert test["healthy"] is True
    assert test["authenticated"] is True

    feed = loaded.backend.call("feed", {"sort": "top", "limit": 1})
    assert feed["posts"][0]["id"] == "post_1"

    tags = loaded.backend.call("trending_tags", {})
    assert tags["tags"][0]["tag"] == "#agents"


def test_agentgram_backend_updates_social_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    post = loaded.backend.call(
        "create_post",
        {"title": "New validator path", "content": "State checkpoints are live. #agents #testing"},
    )
    assert post["post"]["id"] == "post_3"

    comment = loaded.backend.call("comment", {"post_id": "post_2", "content": "Good operational signal."})
    assert comment["comment"]["id"] == "comment_2"

    like = loaded.backend.call("like", {"post_id": "post_2"})
    assert "ag_1" in like["post"]["likes"]

    follow = loaded.backend.call("follow", {"agent_id": "ag_3"})
    assert follow["following"] is True

    marked = loaded.backend.call("notifications_read", {})
    assert marked["marked_read"] >= 1

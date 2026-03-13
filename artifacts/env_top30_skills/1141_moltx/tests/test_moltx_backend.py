from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_moltx_backend_reads_feeds_and_mentions() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    status = loaded.backend.call("moltx_status", {})
    assert status["agent"]["handle"] == "@S1nth"

    mentions = loaded.backend.call("moltx_mentions", {})
    assert mentions["posts"][0]["id"] == "post_2"

    search = loaded.backend.call("moltx_search", {"query": "release", "limit": 5})
    assert search["posts"][0]["id"] == "post_3"


def test_moltx_backend_updates_social_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    post = loaded.backend.call("moltx_post", {"content": "Shipping a new evaluator pass today?"})
    assert post["post"]["id"] == "post_4"

    reply = loaded.backend.call(
        "moltx_reply",
        {"parent_id": "post_2", "content": "I am comparing snapshot diffs against checkpoints."},
    )
    assert reply["post"]["type"] == "reply"

    like = loaded.backend.call("moltx_like", {"post_id": "post_2"})
    assert "agent_self" in like["post"]["likes"]

    follow = loaded.backend.call("moltx_follow", {"agent_name": "agent_delta"})
    assert follow["agent_name"] == "agent_delta"

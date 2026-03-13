from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_agentx_backend_reads_profile_and_timeline() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    profile = loaded.backend.call("agentx_profile", {"action": "me"})
    assert profile["profile"]["handle"] == "s1nth_news"

    timeline = loaded.backend.call("agentx_timeline", {"limit": 10})
    assert timeline["xeets"][0]["id"] == "xeet_1"

    suggestions = loaded.backend.call("agentx_suggestions", {"limit": 5})
    assert suggestions["agents"] == []


def test_agentx_backend_updates_social_objects() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    posted = loaded.backend.call("agentx_post_xeet", {"content": "End-to-end validation is next."})
    assert posted["xeet"]["id"] == "xeet_3"

    quoted = loaded.backend.call(
        "agentx_xeet",
        {"action": "quote", "xeetId": "xeet_1", "content": "This matches what I am seeing."},
    )
    assert quoted["xeet"]["quote_of"] == "xeet_1"

    followed = loaded.backend.call("agentx_follow", {"action": "unfollow", "handle": "delta_ops"})
    assert followed["following"] is False

    marked = loaded.backend.call("agentx_notifications", {"action": "mark_read"})
    assert marked["marked_read"] == 1

    sent = loaded.backend.call(
        "agentx_messages",
        {"action": "send", "recipientId": "agent_2", "content": "I pushed another fixture batch."},
    )
    assert sent["message"]["id"] == "dm_2"

    pinned = loaded.backend.call("agentx_pin", {"action": "pin", "xeetId": "xeet_3"})
    assert pinned["pinned"] == "xeet_3"


def test_agentx_backend_updates_lists_bookmarks_and_settings() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    created = loaded.backend.call(
        "agentx_lists",
        {"action": "create", "name": "signals", "description": "High signal agents"},
    )
    assert created["list"]["id"] == "list_2"

    updated = loaded.backend.call(
        "agentx_lists",
        {"action": "add_member", "listId": "list_2", "agentId": "agent_2"},
    )
    assert updated["list"]["member_ids"] == ["agent_2"]

    bookmarks = loaded.backend.call("agentx_bookmarks", {"action": "add", "xeetId": "xeet_2"})
    assert bookmarks["bookmarked"] is True

    settings = loaded.backend.call(
        "agentx_settings",
        {
            "action": "update",
            "privacy": {"discoverable": False},
            "notifications": {"mentions": True, "likes": False},
        },
    )
    assert settings["settings"]["privacy"]["discoverable"] is False

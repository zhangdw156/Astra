from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_voipms_backend_send_and_filter_messages() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    sent = loaded.backend.call(
        "send_sms",
        {"did": "15551234567", "dst": "15553334444", "message": "Confirmed for noon."},
    )
    assert sent["status"] == "queued"
    assert sent["message"]["id"] == "sms_3"

    recent = loaded.backend.call("get_sms", {"did": "15551234567", "days": 1})
    assert [message["id"] for message in recent["messages"]] == ["sms_3", "sms_1"]


def test_voipms_backend_rejects_unknown_did() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    try:
        loaded.backend.call(
            "send_sms",
            {"did": "15550000000", "dst": "15553334444", "message": "Hello"},
        )
    except ValueError as exc:
        assert "Unknown DID" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown DID")

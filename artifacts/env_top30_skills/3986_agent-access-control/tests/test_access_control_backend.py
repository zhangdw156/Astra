from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_access_control_backend_handles_strangers_and_approvals() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    stranger = loaded.backend.call(
        "handle_stranger",
        {"senderId": "telegram:99", "platform": "telegram", "message": "hello there"},
    )
    assert stranger["status"] == "pending_approval"

    approval = loaded.backend.call(
        "approve_contact",
        {"senderId": "telegram:99", "ownerResponse": "trusted"},
    )
    assert approval["action"] == "approved"

    tier = loaded.backend.call(
        "check_access_tier",
        {"senderId": "telegram:99", "platform": "telegram"},
    )
    assert tier["tier"] == 2

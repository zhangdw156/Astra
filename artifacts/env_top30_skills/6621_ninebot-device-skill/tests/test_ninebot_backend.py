from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_ninebot_backend_authenticates_and_reads_device_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    login = loaded.backend.call(
        "ninebot_login",
        {"username": "demo@example.com", "password": "pass123"},
    )
    assert login["success"] is True

    devices = loaded.backend.call("ninebot_list_devices", {"token": login["token"]})
    assert devices["devices"][0]["sn"] == "NB-001"

    info = loaded.backend.call(
        "ninebot_get_device_info",
        {"token": login["token"], "sn": "NB-001"},
    )
    assert info["battery"] == 78

from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_pager_triage_backend_reads_active_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    incidents = loaded.backend.call("pd_incidents", {})
    assert incidents["total_incidents"] == 2
    assert incidents["incidents"][0]["id"] == "P123ABC"

    detail = loaded.backend.call("pd_incident_detail", {"incident_id": "P123ABC"})
    assert detail["analysis"]["trigger_source"] == "Prometheus Alertmanager"

    services = loaded.backend.call("pd_services", {})
    assert services["services"][0]["id"] == "PSVC123"


def test_pager_triage_backend_requires_confirm_for_writes() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    dry_run = loaded.backend.call("pd_incident_ack", {"incident_id": "P123ABC", "confirm": False})
    assert dry_run["would_update"] is True

    acked = loaded.backend.call("pd_incident_ack", {"incident_id": "P123ABC", "confirm": True})
    assert acked["incident"]["status"] == "acknowledged"

    note = loaded.backend.call(
        "pd_incident_note",
        {"incident_id": "P123ABC", "content": "CPU throttling mitigated.", "confirm": True},
    )
    assert note["note"]["content"] == "CPU throttling mitigated."

    resolved = loaded.backend.call("pd_incident_resolve", {"incident_id": "P123ABC", "confirm": True})
    assert resolved["incident"]["status"] == "resolved"

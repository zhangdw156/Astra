from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_erpclaw_support_backend_runs_issue_workflow() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    issue = loaded.backend.call("add_issue", {"subject": "Printer not syncing"})
    assert issue["issue_id"] == "ISS-0001"

    loaded.backend.call(
        "add_issue_comment",
        {"issue_id": "ISS-0001", "comment": "Investigating"},
    )
    resolved = loaded.backend.call(
        "resolve_issue",
        {"issue_id": "ISS-0001", "resolution_notes": "Restarted sync service"},
    )
    assert resolved["status"] == "resolved"

    report = loaded.backend.call("sla_compliance_report", {})
    assert report["resolved_issues"] == 1

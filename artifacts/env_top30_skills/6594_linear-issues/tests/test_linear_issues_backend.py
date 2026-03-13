from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_linear_backend_reads_lists_and_search() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    mine = loaded.backend.call("list_my_issues", {})
    assert mine["issues"][0]["identifier"] == "ENG-101"

    teams = loaded.backend.call("list_teams", {})
    assert teams["teams"][0]["key"] == "ENG"

    search = loaded.backend.call("search_issues", {"query": "alert"})
    assert search["issues"][0]["identifier"] == "OPS-8"


def test_linear_backend_creates_updates_and_comments() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    created = loaded.backend.call(
        "create_issue",
        {
            "team_id": "team_1",
            "title": "Migrate remaining fixture skills",
            "description": "Continue env backend rollout.",
            "priority": 2,
            "assignee_id": "user_1",
        },
    )
    assert created["issue"]["identifier"] == "ENG-102"

    updated = loaded.backend.call(
        "update_issue",
        {"issue_id": "ENG-102", "state_id": "state_2", "priority": 1},
    )
    assert updated["issue"]["state"]["name"] == "In Progress"
    assert updated["issue"]["priority"] == 1

    comment = loaded.backend.call(
        "add_comment",
        {"issue_id": "ENG-102", "body": "Backend and tests are in place."},
    )
    assert comment["comment"]["id"] == "comment_2"

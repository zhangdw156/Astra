from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_knowledge_graph_backend_tracks_facts_and_summaries() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    added = loaded.backend.call(
        "add_fact",
        {"entity": "people/safa", "category": "status", "fact": "Working on backend migration"},
    )
    assert added["fact"]["id"] == "safa-001"

    loaded.backend.call(
        "supersede_fact",
        {
            "entity": "people/safa",
            "old": "safa-001",
            "category": "status",
            "fact": "Finished backend migration",
        },
    )
    summary = loaded.backend.call("summarize_entity", {"entity": "people/safa"})
    assert "Finished backend migration" in summary["summary"]

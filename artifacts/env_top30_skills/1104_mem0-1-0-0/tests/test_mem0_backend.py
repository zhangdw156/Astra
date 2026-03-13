from __future__ import annotations

from pathlib import Path

import json

from astra.envs.loader import load_backend_from_skill_dir


def test_mem0_hybrid_backend_adds_and_searches_memories() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    added = loaded.backend.call(
        "add_memory",
        {
            "messages": [
                {"role": "user", "content": "Remember that I like weekly summaries"}
            ]
        },
    )
    assert "weekly summaries" in added["memory"]["text"]

    results = loaded.backend.call("search_memories", {"query": "weekly summaries"})
    assert results["results"][0]["id"] == added["memory"]["id"]


def test_mem0_hybrid_profile_declares_no_generated_result_fields() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == []
    assert profile["generated_text_policy"] == "derived-text"

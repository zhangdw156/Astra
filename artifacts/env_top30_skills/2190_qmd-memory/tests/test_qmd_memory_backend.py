from __future__ import annotations

from pathlib import Path

import json

from astra.envs.loader import load_backend_from_skill_dir


def test_qmd_memory_setup_refresh_and_savings() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    setup = loaded.backend.call("setup", {})
    assert setup["configured"] is True

    savings = loaded.backend.call("calculate_savings", {"searches_per_day": 80, "cost_per_call": 0.025})
    assert savings["monthly_savings"] == 60.0

    refreshed = loaded.backend.call("refresh", {})
    assert refreshed["index_version"] == 2


def test_qmd_memory_collection_and_search_flows() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    added = loaded.backend.call(
        "add_collection",
        {"path": "research", "name": "research", "mask": "**/*.md"},
    )
    assert added["collection"]["name"] == "research"

    context = loaded.backend.call(
        "add_context",
        {"collection": "qmd://research", "context": "Market research and long-form analysis"},
    )
    assert context["collection"]["context"] == "Market research and long-form analysis"

    keyword = loaded.backend.call("qmd_search", {"query": "runtime executor", "limit": 5})
    assert keyword["results"][0]["collection"] == "workspace"

    hybrid = loaded.backend.call(
        "qmd_query",
        {"query": "What changed in runtime routing?", "limit": 5},
        conversation_context="We are migrating skills to program backends.",
    )
    assert hybrid["summary"].startswith('Most relevant hit is')


def test_qmd_memory_templates_and_server() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    template = loaded.backend.call("apply_template", {"template": "developer"})
    assert "docs" in template["collections"]

    server = loaded.backend.call("serve", {})
    assert server["status"] == "running"


def test_qmd_memory_hybrid_profile_declares_summary_boundary() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == ["summary"]
    assert profile["generated_text_policy"] == "derived-text"

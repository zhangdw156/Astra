from __future__ import annotations

import json
from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_kontour_plan_trip_extracts_structured_context() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "plan_trip",
        {
            "query": "2 weeks in Japan for a couple, mid-range budget, interested in food and temples",
        },
        conversation_context="The user wants a structured trip brief before building the itinerary.",
    )
    assert result["trip_context"]["destination"]["name"] == "Tokyo"
    assert result["trip_context"]["duration"] == 14
    assert result["trip_context"]["travelers"]["adults"] == 2
    assert result["trip_context"]["budget"]["tier"] == "mid"
    assert result["planning_stage"] in {"develop", "refine"}
    assert result["summary"]
    assert result["recommended_next_question"]


def test_kontour_export_gmaps_builds_urls_and_records_export() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    exported = loaded.backend.call(
        "export_gmaps",
        {"itinerary_file": "sample_tokyo.json", "export_kml": True},
    )
    assert exported["trip_url"].startswith("https://www.google.com/maps/dir/")
    assert exported["day_routes"][0]["day"] == 1
    assert exported["kml_file"] == "sample_tokyo.json.kml"


def test_kontour_hybrid_profile_declares_text_boundaries() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == ["summary", "recommended_next_question"]
    assert profile["generated_text_policy"] == "derived-text"

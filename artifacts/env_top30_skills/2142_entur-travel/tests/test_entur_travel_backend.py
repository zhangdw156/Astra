from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_entur_backend_searches_and_reads_departures() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    search = loaded.backend.call("search", {"query": "Oslo"})
    assert search["results"][0]["id"] == "NSR:StopPlace:59872"

    departures = loaded.backend.call("departures", {"stop_id": "NSR:StopPlace:59872", "limit": 1})
    assert departures["departures"][0]["line"] == "RE10"

    stop = loaded.backend.call("stop", {"stop_id": "NSR:StopPlace:269"})
    assert stop["quays"][0]["publicCode"] == "A"


def test_entur_backend_returns_trip_patterns() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    trip = loaded.backend.call(
        "trip",
        {"from_place": "Oslo S", "to": "Oslo lufthavn", "modes": "rail"},
    )
    assert trip["trips"][0]["legs"][0]["line"] == "RE10"

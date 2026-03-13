from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_flightsearch_backend_returns_sorted_matches() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "flight_search",
        {
            "departure_date": "2026-03-08",
            "departure_city": "北京市",
            "destination_city": "上海市",
        },
    )
    assert result["code"] == 0
    assert [item["航班号"] for item in result["data"]] == ["HO1258", "MU5102"]


def test_flightsearch_backend_returns_empty_for_unknown_route() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "flight_search",
        {
            "departure_date": "2026-03-08",
            "departure_city": "广州市",
            "destination_city": "北京市",
        },
    )
    assert result["data"] == []

from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_unit_convert_backend_executes_real_conversions() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "convert",
        {"value": 100, "from_unit": "cm", "to_unit": "m"},
    )
    assert result["output"] == {"value": 1.0, "unit": "m"}
    assert loaded.backend.snapshot_state()["last_conversion"]["category"] == "length"

    temp_result = loaded.backend.call(
        "convert",
        {"value": 32, "from_unit": "F", "to_unit": "C"},
    )
    assert temp_result["output"] == {"value": 0.0, "unit": "c"}

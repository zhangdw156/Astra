from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_financial_calculator_backend_executes_calculations() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    fv = loaded.backend.call(
        "future_value",
        {"principal": 1000, "rate": 0.05, "years": 2, "compound_frequency": 1},
    )
    assert fv["future_value"] == 1102.5

    discount = loaded.backend.call("discount", {"price": 100, "discount": 20})
    assert discount["final_price"] == 80.0

    launch = loaded.backend.call("launch_ui", {"port": 5051})
    assert launch["status"] == "simulated_launch"
    assert loaded.backend.snapshot_state()["ui_launches"][0]["port"] == 5051

from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_stock_backtester_runs_sma_strategy_on_sample_data() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "run_backtest",
        {
            "csv": "sample",
            "strategy": "sma-crossover",
            "fast-window": 10,
            "slow-window": 30,
            "quiet": True,
        },
    )
    assert result["strategy"] == "sma-crossover"
    assert result["period"]["bars"] > 10
    assert "final_equity" in result["metrics"]


def test_stock_backtester_records_runs_and_supports_breakout() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    result = loaded.backend.call(
        "run_backtest",
        {
            "csv": "sample",
            "strategy": "breakout",
            "lookback": 10,
            "commission-bps": 3,
            "slippage-bps": 1,
            "quiet": True,
        },
    )
    assert result["strategy"] == "breakout"
    assert loaded.backend.snapshot_state()["runs"][0]["trade_count"] == result["metrics"]["trade_count"]

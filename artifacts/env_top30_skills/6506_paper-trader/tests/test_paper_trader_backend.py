from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_paper_trader_backend_updates_account_state() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    loaded.backend.call(
        "init",
        {
            "account": "main",
            "name": "Main",
            "base-currency": "USD",
            "starting-balance": 10000,
        },
    )
    loaded.backend.call(
        "open",
        {
            "account": "main",
            "symbol": "BTC",
            "mint": "btc",
            "side": "LONG",
            "qty": 1,
            "price": 100,
        },
    )
    loaded.backend.call("snapshot", {"symbol": "BTC", "mint": "btc", "price": 120})
    status = loaded.backend.call("status", {"account": "main"})
    assert status["unrealized_pnl"] == 20.0

    close = loaded.backend.call(
        "close",
        {"account": "main", "symbol": "BTC", "qty": 1, "price": 120},
    )
    assert close["realized_pnl"] == 20.0

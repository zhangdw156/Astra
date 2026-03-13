from __future__ import annotations

from pathlib import Path

import json

from astra.envs.loader import load_backend_from_skill_dir


def test_crypto_self_learning_logs_and_analyzes_trades() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    logged = loaded.backend.call(
        "log_trade",
        {
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry": 81000,
            "exit": 82050,
            "pnl_percent": 1.3,
            "result": "WIN",
            "leverage": 4,
            "market_context": '{"day":"friday","hour":10}',
        },
    )
    assert logged["trade"]["id"] == "trade_6"

    analysis = loaded.backend.call(
        "analyze",
        {"symbol": "BTCUSDT", "min_trades": 2},
        conversation_context="The agent wants to reinforce high-conviction long setups.",
    )
    assert analysis["overall"]["total_trades"] >= 2
    assert analysis["summary"].startswith("Analyzed")


def test_crypto_self_learning_generates_rules_and_updates_memory() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    rules = loaded.backend.call("generate_rules", {})
    assert rules["total_rules"] >= 1

    preview = loaded.backend.call(
        "update_memory",
        {"memory_path": "MEMORY.md", "dry_run": True},
    )
    assert preview["updated"] is False
    assert "Learned Rules" in preview["preview"]

    updated = loaded.backend.call(
        "update_memory",
        {"memory_path": "MEMORY.md", "dry_run": False},
    )
    assert updated["updated"] is True


def test_crypto_self_learning_hybrid_profile_declares_summary_boundary() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == ["summary"]
    assert profile["generated_text_policy"] == "derived-text"

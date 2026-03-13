from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}
        self._backtester = self._load_backtester_module()

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "csv_aliases": dict(scenario.get("csv_aliases", {})),
            "runs": [dict(item) for item in scenario.get("runs", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name != "run_backtest":
            raise ValueError(f"Unsupported tool: {tool_name}")
        result = self._run_backtest(arguments)
        self.state["runs"].append(
            {
                "strategy": result["strategy"],
                "csv": str(arguments["csv"]),
                "final_equity": result["metrics"]["final_equity"],
                "trade_count": result["metrics"]["trade_count"],
            }
        )
        return result

    def snapshot_state(self) -> dict:
        return {
            "csv_aliases": dict(self.state["csv_aliases"]),
            "runs": [dict(item) for item in self.state["runs"]],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _run_backtest(self, arguments: dict) -> dict:
        csv_path = self._resolve_csv_path(str(arguments["csv"]))
        args = SimpleNamespace(
            csv=str(csv_path),
            strategy=str(arguments["strategy"]),
            initial_capital=float(arguments.get("initial-capital", 100000)),
            commission_bps=float(arguments.get("commission-bps", 5)),
            slippage_bps=float(arguments.get("slippage-bps", 2)),
            risk_free_rate=float(arguments.get("risk-free-rate", 0.02)),
            fast_window=int(arguments.get("fast-window", 20)),
            slow_window=int(arguments.get("slow-window", 60)),
            rsi_period=int(arguments.get("rsi-period", 14)),
            rsi_entry=float(arguments.get("rsi-entry", 30)),
            rsi_exit=float(arguments.get("rsi-exit", 55)),
            lookback=int(arguments.get("lookback", 20)),
            quiet=bool(arguments.get("quiet", True)),
        )
        self._backtester.validate_args(args)
        bars = self._backtester.load_bars(csv_path)
        return self._backtester.run_backtest(args, bars)

    def _resolve_csv_path(self, raw_csv: str) -> Path:
        alias_or_path = str(raw_csv).strip()
        relative = self.state["csv_aliases"].get(alias_or_path, alias_or_path)
        path = (self.skill_dir / relative).resolve() if not Path(relative).is_absolute() else Path(relative)
        if not path.exists():
            raise FileNotFoundError(f"CSV not found: {alias_or_path}")
        return path

    def _load_backtester_module(self):
        module_path = self.skill_dir / "scripts" / "backtest_strategy.py"
        spec = importlib.util.spec_from_file_location("astra_stock_backtester", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load backtester from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

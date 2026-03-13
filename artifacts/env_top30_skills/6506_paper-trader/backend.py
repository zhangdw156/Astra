from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "accounts": dict(scenario.get("accounts", {})),
            "snapshots": dict(scenario.get("snapshots", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        handlers = {
            "init": self._init_account,
            "snapshot": self._snapshot,
            "open": self._open_position,
            "set_levels": self._set_levels,
            "close": self._close_position,
            "note": self._add_note,
            "status": self._status,
            "review": self._review,
        }
        return handlers[tool_name](arguments)

    def snapshot_state(self) -> dict:
        return {"accounts": dict(self.state["accounts"]), "snapshots": dict(self.state["snapshots"])}

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _init_account(self, arguments: dict) -> dict:
        account_id = str(arguments["account"])
        self.state["accounts"][account_id] = {
            "name": str(arguments["name"]),
            "base_currency": str(arguments["base-currency"]),
            "balance": float(arguments["starting-balance"]),
            "realized_pnl": 0.0,
            "positions": [],
            "notes": [],
        }
        return {"account": account_id, "initialized": True}

    def _snapshot(self, arguments: dict) -> dict:
        symbol = str(arguments["symbol"])
        price = float(arguments.get("price", 0.0))
        self.state["snapshots"][symbol] = {
            "mint": str(arguments["mint"]),
            "price": price,
            "source": str(arguments.get("source", "dexscreener")),
        }
        return {"symbol": symbol, "price": price}

    def _open_position(self, arguments: dict) -> dict:
        account = self._account(arguments["account"])
        position = {
            "symbol": str(arguments["symbol"]),
            "mint": str(arguments["mint"]),
            "side": str(arguments["side"]),
            "qty": float(arguments["qty"]),
            "price": float(arguments.get("price", 0.0)),
            "stop_price": float(arguments.get("stop-price", 0.0)),
            "take_price": float(arguments.get("take-price", 0.0)),
        }
        account["positions"].append(position)
        return {"opened": True, "position": position}

    def _set_levels(self, arguments: dict) -> dict:
        position = self._find_position(arguments["account"], arguments["symbol"])
        if "stop-price" in arguments:
            position["stop_price"] = float(arguments["stop-price"])
        if "take-price" in arguments:
            position["take_price"] = float(arguments["take-price"])
        return {"updated": True, "position": position}

    def _close_position(self, arguments: dict) -> dict:
        account = self._account(arguments["account"])
        position = self._find_position(arguments["account"], arguments["symbol"])
        qty = float(arguments["qty"])
        exit_price = float(arguments.get("price", self.state["snapshots"].get(position["symbol"], {}).get("price", 0.0)))
        pnl = (exit_price - position["price"]) * qty
        if position["side"] == "SHORT":
            pnl *= -1
        account["realized_pnl"] += pnl
        position["qty"] -= qty
        if position["qty"] <= 0:
            account["positions"] = [p for p in account["positions"] if p["qty"] > 0]
        return {"closed_qty": qty, "realized_pnl": round(pnl, 2)}

    def _add_note(self, arguments: dict) -> dict:
        account = self._account(arguments["account"])
        note = {"symbol": str(arguments["symbol"]), "note": str(arguments["note"])}
        account["notes"].append(note)
        return {"note_added": True, "note": note}

    def _status(self, arguments: dict) -> dict:
        account = self._account(arguments["account"])
        unrealized = 0.0
        for position in account["positions"]:
            snapshot = self.state["snapshots"].get(position["symbol"])
            if snapshot:
                diff = snapshot["price"] - position["price"]
                if position["side"] == "SHORT":
                    diff *= -1
                unrealized += diff * position["qty"]
        return {
            "account": str(arguments["account"]),
            "open_positions": len(account["positions"]),
            "realized_pnl": round(account["realized_pnl"], 2),
            "unrealized_pnl": round(unrealized, 2),
        }

    def _review(self, arguments: dict) -> dict:
        status = self._status(arguments)
        return {
            "account": status["account"],
            "trade_count": len(self._account(arguments["account"])["notes"]) + len(self._account(arguments["account"])["positions"]),
            "realized_pnl": status["realized_pnl"],
        }

    def _account(self, account_id: str) -> dict:
        return self.state["accounts"][str(account_id)]

    def _find_position(self, account_id: str, symbol: str) -> dict:
        account = self._account(account_id)
        for position in account["positions"]:
            if position["symbol"] == str(symbol):
                return position
        raise ValueError(f"Unknown position for symbol: {symbol}")

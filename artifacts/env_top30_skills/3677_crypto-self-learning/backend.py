from __future__ import annotations

import json
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "trades": [self._copy_trade(item) for item in scenario.get("trades", [])],
            "learned_rules": [dict(item) for item in scenario.get("learned_rules", [])],
            "memory_documents": dict(scenario.get("memory_documents", {})),
            "next_trade_id": int(scenario.get("next_trade_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "log_trade":
            return self._log_trade(arguments)
        if tool_name == "analyze":
            return self._analyze(arguments, conversation_context)
        if tool_name == "generate_rules":
            return self._generate_rules()
        if tool_name == "update_memory":
            return self._update_memory(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "trades": [self._copy_trade(item) for item in self.state["trades"]],
            "learned_rules": [dict(item) for item in self.state["learned_rules"]],
            "memory_documents": dict(self.state["memory_documents"]),
            "next_trade_id": self.state["next_trade_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _log_trade(self, arguments: dict) -> dict:
        if arguments.get("stats"):
            return self._stats()
        if arguments.get("list"):
            last = int(arguments.get("last", len(self.state["trades"])))
            return {"trades": [self._present_trade(item) for item in self.state["trades"][-last:]]}

        trade = {
            "id": f"trade_{self.state['next_trade_id']}",
            "timestamp": "2026-03-13T10:00:00Z",
            "symbol": str(arguments["symbol"]).upper(),
            "direction": str(arguments["direction"]).upper(),
            "entry": float(arguments["entry"]),
            "exit": float(arguments["exit"]),
            "pnl_percent": float(arguments["pnl_percent"]),
            "result": str(arguments["result"]).upper(),
            "leverage": int(arguments["leverage"]) if arguments.get("leverage") is not None else None,
            "reason": str(arguments.get("reason", "")),
            "indicators": self._parse_json(arguments.get("indicators")),
            "market_context": self._parse_json(arguments.get("market_context")),
            "notes": str(arguments.get("notes", "")),
            "day_of_week": self._extract_day(arguments.get("market_context")),
            "hour": self._extract_hour(arguments.get("market_context")),
        }
        self.state["next_trade_id"] += 1
        self.state["trades"].append(trade)
        return {"trade": self._present_trade(trade)}

    def _analyze(self, arguments: dict, conversation_context: str | None) -> dict:
        trades = self._filtered_trades(arguments)
        min_trades = int(arguments.get("min_trades", 3))
        if len(trades) < min_trades:
            return {"overall": {"total_trades": len(trades)}, "insights": [], "summary": "Not enough trades for analysis."}

        overall = self._overall_stats(trades)
        by_direction = self._group_stats(trades, "direction", min_trades)
        by_day = self._group_stats(trades, "day_of_week", min_trades)
        insights = self._derive_insights(overall, by_direction, by_day)
        summary = self._synthesize_analysis_summary(overall, insights, conversation_context)
        return {
            "overall": overall,
            "by_direction": by_direction,
            "by_day": by_day,
            "insights": insights,
            "summary": summary,
        }

    def _generate_rules(self) -> dict:
        trades = list(self.state["trades"])
        rules = []
        direction_stats = self._group_stats(trades, "direction", min_trades=2)
        for stat in direction_stats:
            if stat["win_rate"] >= 65:
                rules.append(self._rule("PREFER", "direction", f"PREFER {stat['value']} positions", stat))
            elif stat["win_rate"] <= 35:
                rules.append(self._rule("AVOID", "direction", f"AVOID {stat['value']} positions", stat))

        day_stats = self._group_stats(trades, "day_of_week", min_trades=2)
        for stat in day_stats:
            if stat["win_rate"] >= 75:
                rules.append(self._rule("PREFER", "timing", f"PREFER trading on {stat['value'].title()}", stat))
            elif stat["win_rate"] <= 25:
                rules.append(self._rule("AVOID", "timing", f"AVOID trading on {stat['value'].title()}", stat))

        high_lev = [trade for trade in trades if trade.get("leverage") and trade["leverage"] >= 10]
        if len(high_lev) >= 1:
            wr = self._win_rate(high_lev)
            if wr <= 45:
                rules.append(
                    {
                        "type": "AVOID",
                        "category": "risk",
                        "rule": "AVOID leverage >= 10x",
                        "evidence": f"Win rate: {wr:.0f}% over {len(high_lev)} high-leverage trades",
                        "confidence": "MEDIUM" if len(high_lev) < 3 else "HIGH",
                    }
                )

        self.state["learned_rules"] = rules
        return {"rules": [dict(item) for item in rules], "total_rules": len(rules)}

    def _update_memory(self, arguments: dict) -> dict:
        memory_path = str(arguments["memory_path"])
        if memory_path not in self.state["memory_documents"]:
            self.state["memory_documents"][memory_path] = "# Trading Memory\n"
        rules_section = self._memory_section()
        content = self.state["memory_documents"][memory_path].rstrip()
        updated = f"{content}\n\n{rules_section}\n"
        if bool(arguments.get("dry_run", False)):
            return {"memory_path": memory_path, "preview": rules_section, "updated": False}
        self.state["memory_documents"][memory_path] = updated
        return {"memory_path": memory_path, "updated": True, "rule_count": len(self.state["learned_rules"])}

    def _filtered_trades(self, arguments: dict) -> list[dict]:
        trades = list(self.state["trades"])
        symbol = str(arguments.get("symbol", "")).strip().upper()
        direction = str(arguments.get("direction", "")).strip().upper()
        if symbol:
            trades = [trade for trade in trades if trade["symbol"] == symbol]
        if direction:
            trades = [trade for trade in trades if trade["direction"] == direction]
        return trades

    def _overall_stats(self, trades: list[dict]) -> dict:
        total_pnl = round(sum(trade["pnl_percent"] for trade in trades), 2)
        wins = [trade for trade in trades if trade["result"] == "WIN"]
        return {
            "total_trades": len(trades),
            "win_rate": round(self._win_rate(trades), 2),
            "total_pnl": total_pnl,
            "wins": len(wins),
            "losses": len(trades) - len(wins),
        }

    def _group_stats(self, trades: list[dict], field: str, min_trades: int) -> list[dict]:
        groups: dict[str, list[dict]] = {}
        for trade in trades:
            value = trade.get(field)
            if value is None:
                continue
            groups.setdefault(str(value), []).append(trade)
        stats = []
        for value, items in groups.items():
            if len(items) < min_trades:
                continue
            avg_pnl = sum(item["pnl_percent"] for item in items) / len(items)
            stats.append(
                {
                    "value": value,
                    "win_rate": round(self._win_rate(items), 2),
                    "n": len(items),
                    "avg_pnl": round(avg_pnl, 2),
                }
            )
        stats.sort(key=lambda item: item["win_rate"], reverse=True)
        return stats

    def _derive_insights(self, overall: dict, by_direction: list[dict], by_day: list[dict]) -> list[dict]:
        insights = []
        baseline = overall["win_rate"]
        for stat in by_direction + by_day:
            delta = stat["win_rate"] - baseline
            if abs(delta) < 10:
                continue
            insights.append(
                {
                    "action": "PREFER" if delta > 0 else "AVOID",
                    "message": f"{stat['value']} shows {stat['win_rate']:.0f}% win rate over {stat['n']} trades",
                    "impact": round(delta, 2),
                }
            )
        insights.sort(key=lambda item: abs(item["impact"]), reverse=True)
        return insights

    def _synthesize_analysis_summary(
        self,
        overall: dict,
        insights: list[dict],
        conversation_context: str | None,
    ) -> str:
        head = f"Analyzed {overall['total_trades']} trades with {overall['win_rate']:.1f}% win rate."
        if insights:
            head += f" Top pattern: {insights[0]['action']} because {insights[0]['message']}."
        if conversation_context:
            head += f" Context: {conversation_context[:80]}"
        return head

    def _memory_section(self) -> str:
        if not self.state["learned_rules"]:
            return "## Learned Rules\n- No confident rules generated yet."
        lines = ["## Learned Rules"]
        for rule in self.state["learned_rules"]:
            lines.append(f"- {rule['type']}: {rule['rule']} ({rule['evidence']})")
        return "\n".join(lines)

    def _stats(self) -> dict:
        overall = self._overall_stats(self.state["trades"])
        return {"stats": overall}

    def _rule(self, rule_type: str, category: str, text: str, stat: dict) -> dict:
        return {
            "type": rule_type,
            "category": category,
            "rule": text,
            "evidence": f"Win rate: {stat['win_rate']:.0f}% over {stat['n']} trades",
            "confidence": "HIGH" if stat["n"] >= 3 else "MEDIUM",
        }

    def _parse_json(self, raw: object) -> dict:
        if raw is None or raw == "":
            return {}
        if isinstance(raw, dict):
            return dict(raw)
        return json.loads(str(raw))

    def _extract_day(self, market_context: object) -> str:
        data = self._parse_json(market_context)
        return str(data.get("day", "friday")).lower()

    def _extract_hour(self, market_context: object) -> int:
        data = self._parse_json(market_context)
        return int(data.get("hour", 10))

    def _win_rate(self, trades: list[dict]) -> float:
        if not trades:
            return 0.0
        wins = len([trade for trade in trades if trade["result"] == "WIN"])
        return wins / len(trades) * 100

    def _present_trade(self, trade: dict) -> dict:
        return {
            "id": trade["id"],
            "symbol": trade["symbol"],
            "direction": trade["direction"],
            "pnl_percent": trade["pnl_percent"],
            "result": trade["result"],
            "leverage": trade["leverage"],
        }

    def _copy_trade(self, trade: dict) -> dict:
        return {
            "id": trade["id"],
            "timestamp": trade["timestamp"],
            "symbol": trade["symbol"],
            "direction": trade["direction"],
            "entry": float(trade["entry"]),
            "exit": float(trade["exit"]),
            "pnl_percent": float(trade["pnl_percent"]),
            "result": trade["result"],
            "leverage": trade.get("leverage"),
            "reason": trade.get("reason", ""),
            "indicators": dict(trade.get("indicators", {})),
            "market_context": dict(trade.get("market_context", {})),
            "notes": trade.get("notes", ""),
            "day_of_week": trade.get("day_of_week"),
            "hour": trade.get("hour"),
        }

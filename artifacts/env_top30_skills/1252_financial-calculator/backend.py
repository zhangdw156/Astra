from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "last_calculation": scenario.get("last_calculation"),
            "ui_launches": list(scenario.get("ui_launches", [])),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        handlers = {
            "future_value": self._future_value,
            "present_value": self._present_value,
            "discount": self._discount,
            "markup": self._markup,
            "future_value_table": self._future_value_table,
            "discount_table": self._discount_table,
            "launch_ui": self._launch_ui,
        }
        if tool_name not in handlers:
            raise ValueError(f"Unsupported tool: {tool_name}")
        result = handlers[tool_name](arguments)
        self.state["last_calculation"] = {"tool": tool_name, "result": result}
        return result

    def snapshot_state(self) -> dict:
        return {
            "last_calculation": self.state.get("last_calculation"),
            "ui_launches": list(self.state.get("ui_launches", [])),
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _future_value(self, arguments: dict) -> dict:
        principal = float(arguments["principal"])
        rate = float(arguments["rate"])
        years = int(arguments["years"])
        frequency = int(arguments.get("compound_frequency", 1))
        value = principal * (1 + rate / frequency) ** (frequency * years)
        return {
            "principal": principal,
            "rate": rate,
            "years": years,
            "compound_frequency": frequency,
            "future_value": round(value, 2),
            "interest_earned": round(value - principal, 2),
        }

    def _present_value(self, arguments: dict) -> dict:
        future_value = float(arguments["future_value"])
        rate = float(arguments["rate"])
        years = int(arguments["years"])
        frequency = int(arguments.get("compound_frequency", 1))
        value = future_value / (1 + rate / frequency) ** (frequency * years)
        return {
            "future_value": future_value,
            "rate": rate,
            "years": years,
            "compound_frequency": frequency,
            "present_value": round(value, 2),
        }

    def _discount(self, arguments: dict) -> dict:
        price = float(arguments["price"])
        discount = self._normalize_percentage(float(arguments["discount"]))
        discount_amount = price * discount
        return {
            "price": price,
            "discount_rate": discount,
            "discount_amount": round(discount_amount, 2),
            "final_price": round(price - discount_amount, 2),
        }

    def _markup(self, arguments: dict) -> dict:
        cost = float(arguments["cost"])
        markup = self._normalize_percentage(float(arguments["markup"]))
        markup_amount = cost * markup
        selling_price = cost + markup_amount
        return {
            "cost": cost,
            "markup_rate": markup,
            "markup_amount": round(markup_amount, 2),
            "selling_price": round(selling_price, 2),
            "profit_margin": round(markup_amount / selling_price, 4) if selling_price else 0.0,
        }

    def _future_value_table(self, arguments: dict) -> dict:
        principal = float(arguments["principal"])
        rates = [float(rate) for rate in arguments["rates"]]
        periods = [int(period) for period in arguments["periods"]]
        rows = []
        for rate in rates:
            for years in periods:
                fv = self._future_value(
                    {
                        "principal": principal,
                        "rate": rate,
                        "years": years,
                        "compound_frequency": 1,
                    }
                )
                rows.append(
                    {
                        "rate": rate,
                        "years": years,
                        "future_value": fv["future_value"],
                    }
                )
        return {"principal": principal, "rows": rows}

    def _discount_table(self, arguments: dict) -> dict:
        price = float(arguments["price"])
        discounts = [float(value) for value in arguments["discounts"]]
        rows = []
        for value in discounts:
            result = self._discount({"price": price, "discount": value})
            rows.append(
                {
                    "discount_input": value,
                    "discount_rate": result["discount_rate"],
                    "final_price": result["final_price"],
                }
            )
        return {"price": price, "rows": rows}

    def _launch_ui(self, arguments: dict) -> dict:
        port = int(arguments.get("port", 5050))
        launch = {
            "port": port,
            "url": f"http://127.0.0.1:{port}",
            "status": "simulated_launch",
        }
        self.state.setdefault("ui_launches", []).append(launch)
        return launch

    def _normalize_percentage(self, value: float) -> float:
        if value > 1:
            return value / 100.0
        return value

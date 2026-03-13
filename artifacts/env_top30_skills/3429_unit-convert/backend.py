from __future__ import annotations

from pathlib import Path


class SkillBackend:
    CATEGORY_FACTORS = {
        "length": {
            "mm": 0.001,
            "cm": 0.01,
            "m": 1.0,
            "km": 1000.0,
            "in": 0.0254,
            "ft": 0.3048,
            "yd": 0.9144,
            "mi": 1609.344,
        },
        "weight": {
            "mg": 0.000001,
            "g": 0.001,
            "kg": 1.0,
            "t": 1000.0,
            "oz": 0.028349523125,
            "lb": 0.45359237,
            "stone": 6.35029318,
        },
        "area": {
            "mm2": 0.000001,
            "cm2": 0.0001,
            "m2": 1.0,
            "km2": 1000000.0,
            "in2": 0.00064516,
            "ft2": 0.09290304,
            "yd2": 0.83612736,
            "acre": 4046.8564224,
            "mi2": 2589988.110336,
        },
        "volume": {
            "ml": 0.001,
            "l": 1.0,
            "kl": 1000.0,
            "floz": 0.0295735295625,
            "cup": 0.2365882365,
            "pt": 0.473176473,
            "qt": 0.946352946,
            "gal": 3.785411784,
        },
        "speed": {
            "ms": 1.0,
            "kmh": 0.2777777777777778,
            "fts": 0.3048,
            "mph": 0.44704,
            "knot": 0.5144444444444445,
        },
        "time": {
            "ms": 0.001,
            "s": 1.0,
            "min": 60.0,
            "h": 3600.0,
            "day": 86400.0,
            "week": 604800.0,
            "year": 31536000.0,
        },
        "data": {
            "b": 1.0,
            "kb": 1024.0,
            "mb": 1024.0**2,
            "gb": 1024.0**3,
            "tb": 1024.0**4,
            "pb": 1024.0**5,
        },
    }

    ALIASES = {
        "inch": "in",
        "inches": "in",
        "foot": "ft",
        "feet": "ft",
        "yard": "yd",
        "yards": "yd",
        "mile": "mi",
        "miles": "mi",
        "ounce": "oz",
        "ounces": "oz",
        "pound": "lb",
        "pounds": "lb",
        "milliliter": "ml",
        "milliliters": "ml",
        "liter": "l",
        "liters": "l",
        "kiloliter": "kl",
        "kiloliters": "kl",
        "minute": "min",
        "minutes": "min",
        "second": "s",
        "seconds": "s",
        "millisecond": "ms",
        "milliseconds": "ms",
        "hour": "h",
        "hours": "h",
        "byte": "b",
        "bytes": "b",
        "fl oz": "floz",
        "m/s": "ms",
        "km/h": "kmh",
        "ft/s": "fts",
    }

    TEMPERATURE_UNITS = {"c", "f", "k"}

    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {"last_conversion": scenario.get("last_conversion")}

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "convert":
            return self._convert(arguments)
        if tool_name == "list_units":
            return self._list_units(arguments)
        if tool_name == "categories":
            return {"categories": sorted(self.CATEGORY_FACTORS.keys() | {"temperature"})}
        if tool_name == "help":
            return self._help(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return dict(self.state)

    def visible_state(self) -> dict:
        return dict(self.state)

    def _convert(self, arguments: dict) -> dict:
        value = float(arguments["value"])
        from_unit = self._normalize_unit(str(arguments["from_unit"]))
        to_unit = self._normalize_unit(str(arguments["to_unit"]))
        category = self._category_for_units(from_unit, to_unit)

        if category == "temperature":
            converted = self._convert_temperature(value, from_unit, to_unit)
        else:
            base_value = value * self.CATEGORY_FACTORS[category][from_unit]
            converted = base_value / self.CATEGORY_FACTORS[category][to_unit]

        result = {
            "category": category,
            "input": {"value": value, "unit": from_unit},
            "output": {"value": round(converted, 6), "unit": to_unit},
        }
        self.state["last_conversion"] = result
        return result

    def _list_units(self, arguments: dict) -> dict:
        category = str(arguments["category"]).strip().lower()
        if category == "temperature":
            units = sorted(self.TEMPERATURE_UNITS)
        else:
            units = sorted(self.CATEGORY_FACTORS[category].keys())
        return {"category": category, "units": units}

    def _help(self, arguments: dict) -> dict:
        category = str(arguments["category"]).strip().lower()
        return {
            "category": category,
            "units": self._list_units({"category": category})["units"],
            "notes": f"Use convert to translate values within the {category} category.",
        }

    def _normalize_unit(self, unit: str) -> str:
        canonical = unit.strip().lower().replace("²", "2")
        return self.ALIASES.get(canonical, canonical)

    def _category_for_units(self, from_unit: str, to_unit: str) -> str:
        if from_unit in self.TEMPERATURE_UNITS and to_unit in self.TEMPERATURE_UNITS:
            return "temperature"
        for category, factors in self.CATEGORY_FACTORS.items():
            if from_unit in factors and to_unit in factors:
                return category
        raise ValueError(f"Incompatible units: {from_unit} -> {to_unit}")

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        celsius = value
        if from_unit == "f":
            celsius = (value - 32.0) * 5.0 / 9.0
        elif from_unit == "k":
            celsius = value - 273.15

        if to_unit == "c":
            return celsius
        if to_unit == "f":
            return celsius * 9.0 / 5.0 + 32.0
        return celsius + 273.15

from __future__ import annotations

import math
import re
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "formulas": {
                key: [dict(item) for item in value]
                for key, value in scenario.get("formulas", {}).items()
            },
            "practice_templates": {
                key: [dict(item) for item in value]
                for key, value in scenario.get("practice_templates", {}).items()
            },
            "history": [dict(item) for item in scenario.get("history", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "solve":
            result = self._solve_problem(str(arguments["problem"]))
            self._record("solve", arguments, result)
            return result
        if tool_name == "step":
            result = self._step_problem(str(arguments["problem"]))
            self._record("step", arguments, result)
            return result
        if tool_name == "graph":
            result = self._graph_function(str(arguments["function"]))
            self._record("graph", arguments, result)
            return result
        if tool_name == "formula":
            result = self._formula_topic(str(arguments["topic"]))
            self._record("formula", arguments, result)
            return result
        if tool_name == "convert":
            result = self._convert_units(str(arguments["conversion"]))
            self._record("convert", arguments, result)
            return result
        if tool_name == "practice":
            result = self._practice(str(arguments["topic"]), int(arguments.get("count", 10)))
            self._record("practice", arguments, result)
            return result
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "formulas": {
                key: [dict(item) for item in value]
                for key, value in self.state["formulas"].items()
            },
            "practice_templates": {
                key: [dict(item) for item in value]
                for key, value in self.state["practice_templates"].items()
            },
            "history": [dict(item) for item in self.state["history"]],
        }

    def visible_state(self) -> dict:
        return {"history": [dict(item) for item in self.state["history"]]}

    def _solve_problem(self, problem: str) -> dict:
        linear = re.fullmatch(r"\s*([+-]?\d*)x\s*([+-]\s*\d+)\s*=\s*([+-]?\d+)\s*", problem.replace(" ", ""))
        if linear:
            a_text, b_text, c_text = linear.groups()
            a = -1 if a_text == "-" else 1 if a_text in {"", "+"} else int(a_text)
            b = int(b_text.replace(" ", ""))
            c = int(c_text)
            x = (c - b) / a
            return {
                "problem": problem,
                "answer": f"x = {self._fmt_number(x)}",
                "solution": f"Move {b} to the right side, then divide by {a}.",
                "summary": f"Solved the linear equation and found x = {self._fmt_number(x)}.",
                "verification": f"{a}*{self._fmt_number(x)} + ({b}) = {c}",
            }

        derivative = re.fullmatch(r"\s*(?:求导|derive)\s*(?:of)?\s*x\^(\d+)([+-]\d+x)?\s*", problem, re.IGNORECASE)
        if derivative:
            power = int(derivative.group(1))
            linear_term = derivative.group(2)
            coeff = int(linear_term[:-1]) if linear_term else 0
            pieces = [f"{power}x^{power-1}" if power - 1 != 1 else f"{power}x"]
            if power == 1:
                pieces = [str(power)]
            if coeff:
                pieces.append(str(coeff))
            answer = " + ".join(pieces).replace("+ -", "- ")
            return {
                "problem": problem,
                "answer": answer,
                "solution": "Apply the power rule term by term.",
                "summary": f"Computed the derivative as {answer}.",
                "verification": "Each polynomial term was differentiated independently.",
            }

        raise ValueError(f"Unsupported problem format: {problem}")

    def _step_problem(self, problem: str) -> dict:
        solved = self._solve_problem(problem)
        answer = solved["answer"]
        if answer.startswith("x = "):
            value = answer.split("=", 1)[1].strip()
            steps = [
                f"Start with {problem}.",
                "Isolate the x-term by moving the constant to the other side.",
                f"Divide both sides by the coefficient of x to get x = {value}.",
            ]
        else:
            steps = [
                f"Start with {problem}.",
                "Differentiate each term separately using the power rule.",
                f"Combine the differentiated terms to get {answer}.",
            ]
        return {
            "problem": problem,
            "answer": answer,
            "steps": steps,
            "summary": solved["summary"],
            "tips": ["Check signs carefully.", "Verify by substitution when possible."],
        }

    def _graph_function(self, function: str) -> dict:
        normalized = function.replace(" ", "")
        if normalized in {"y=x^2", "f(x)=x^2"}:
            return {
                "function": function,
                "domain": "all real numbers",
                "range": "y >= 0",
                "intercepts": {"x": [(0, 0)], "y": (0, 0)},
                "ascii_graph": "\n".join(
                    [
                        "    y",
                        "    |      *",
                        "  2 +    *   *",
                        "  1 +  *       *",
                        "  0 +*----*----*----> x",
                        "     -2   0    2",
                    ]
                ),
                "summary": "This is an upward-opening parabola with vertex at the origin.",
            }
        if normalized in {"y=1/x", "f(x)=1/x"}:
            return {
                "function": function,
                "domain": "x != 0",
                "range": "y != 0",
                "intercepts": {"x": [], "y": None},
                "ascii_graph": "\n".join(
                    [
                        "    y",
                        "    |   *",
                        "  1 +    *",
                        "  0 +-----+-----> x",
                        " -1 + *",
                        "    |*",
                    ]
                ),
                "summary": "This is a reciprocal curve with asymptotes x = 0 and y = 0.",
            }
        raise ValueError(f"Unsupported function format: {function}")

    def _formula_topic(self, topic: str) -> dict:
        key = topic.strip().lower()
        mapping = {
            "algebra": "algebra",
            "geometry": "geometry",
            "calculus": "calculus",
            "微积分": "calculus",
            "几何": "geometry",
            "代数": "algebra",
        }
        resolved = mapping.get(key, key)
        formulas = self.state["formulas"].get(resolved)
        if not formulas:
            raise ValueError(f"Unknown formula topic: {topic}")
        return {"topic": resolved, "formulas": [dict(item) for item in formulas]}

    def _convert_units(self, conversion: str) -> dict:
        match = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*([A-Za-z]+)\s+to\s+([A-Za-z]+)\s*", conversion)
        if not match:
            raise ValueError(f"Unsupported conversion format: {conversion}")
        value = float(match.group(1))
        src = match.group(2).lower()
        dst = match.group(3).lower()

        if (src, dst) == ("km", "miles"):
            converted = value * 0.621371
            formula = "miles = km * 0.621371"
        elif (src, dst) == ("kg", "pounds"):
            converted = value * 2.20462
            formula = "pounds = kg * 2.20462"
        elif (src, dst) == ("f", "c"):
            converted = (value - 32) * 5 / 9
            formula = "C = (F - 32) * 5/9"
        elif (src, dst) == ("c", "f"):
            converted = value * 9 / 5 + 32
            formula = "F = C * 9/5 + 32"
        else:
            raise ValueError(f"Unsupported conversion pair: {src} -> {dst}")

        return {
            "conversion": conversion,
            "value": self._fmt_number(value),
            "from_unit": src,
            "to_unit": dst,
            "converted_value": self._fmt_number(converted),
            "formula": formula,
            "summary": f"{self._fmt_number(value)} {src} = {self._fmt_number(converted)} {dst}",
        }

    def _practice(self, topic: str, count: int) -> dict:
        templates = self.state["practice_templates"].get(topic)
        if not templates:
            raise ValueError(f"Unknown practice topic: {topic}")
        items = [dict(templates[i % len(templates)]) for i in range(max(count, 1))]
        return {
            "topic": topic,
            "count": len(items),
            "problems": items,
            "summary": f"Generated {len(items)} practice problems for {topic}.",
        }

    def _record(self, tool_name: str, arguments: dict, result: dict) -> None:
        self.state["history"].append(
            {
                "tool_name": tool_name,
                "arguments": dict(arguments),
                "result_keys": sorted(result.keys()),
            }
        )

    def _fmt_number(self, value: float) -> str:
        if float(value).is_integer():
            return str(int(value))
        return f"{value:.4f}".rstrip("0").rstrip(".")

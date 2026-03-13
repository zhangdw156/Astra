from __future__ import annotations

import json
from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_math_solver_solves_steps_and_converts() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    solved = loaded.backend.call("solve", {"problem": "2x+3=11"})
    assert solved["answer"] == "x = 4"

    stepped = loaded.backend.call("step", {"problem": "2x+3=11"})
    assert stepped["steps"][0].startswith("Start with")
    assert stepped["summary"]

    converted = loaded.backend.call("convert", {"conversion": "5km to miles"})
    assert converted["converted_value"] == "3.1069"


def test_math_solver_graph_formula_and_practice() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    graph = loaded.backend.call("graph", {"function": "y=x^2"})
    assert "parabola" in graph["summary"].lower()
    assert "ascii_graph" in graph

    formulas = loaded.backend.call("formula", {"topic": "calculus"})
    assert formulas["formulas"][0]["name"] == "Power Rule"

    practice = loaded.backend.call("practice", {"topic": "初中代数", "count": 3})
    assert practice["count"] == 3
    assert practice["problems"][0]["problem"] == "2x + 3 = 11"


def test_math_solver_hybrid_profile_declares_text_boundaries() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    profile = json.loads((skill_dir / "environment_profile.json").read_text(encoding="utf-8"))
    assert profile["state_mutation_policy"] == "programmatic"
    assert profile["generated_result_fields"] == ["summary", "solution", "steps", "ascii_graph", "tips"]
    assert profile["generated_text_policy"] == "derived-text"

from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_openclaw_code_search_fixture_backend_supports_fixture_queries() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    grep = loaded.backend.call("grep", {"pattern": "class", "type": "py"})
    assert grep["results"][0]["path"] == "src/agent.py"

    glob = loaded.backend.call("glob", {"pattern": "*SKILL*", "type": "f"})
    assert glob["matches"] == ["skills/demo/SKILL.md"]

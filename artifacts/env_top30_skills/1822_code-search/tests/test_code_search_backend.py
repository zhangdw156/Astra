from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_code_search_fixture_backend_supports_grep_glob_and_tree() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    grep = loaded.backend.call("grep", {"pattern": "def", "type": "py"})
    assert grep["results"][0]["path"] == "src/main.py"

    glob = loaded.backend.call("glob", {"pattern": "*test*", "type": "f"})
    assert glob["matches"] == ["tests/test_main.py"]

    tree = loaded.backend.call("tree", {"depth": 2})
    assert "README.md" in tree["nodes"]

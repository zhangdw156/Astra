from __future__ import annotations

from pathlib import Path

from astra.envs.loader import load_backend_from_skill_dir


def test_workspace_files_backend_reads_writes_and_searches() -> None:
    skill_dir = Path(__file__).resolve().parents[1]
    loaded = load_backend_from_skill_dir(skill_dir)
    assert loaded is not None

    listing = loaded.backend.call("list_dir", {"path": "."})
    assert "TOOLS.md" in listing["entries"]

    loaded.backend.call("write_file", {"path": "07_OUTPUTS/demo.txt", "content": "hello"})
    content = loaded.backend.call("read_file", {"path": "07_OUTPUTS/demo.txt"})
    assert content["content"] == "hello"

    search = loaded.backend.call("search_files", {"pattern": "demo"})
    assert search["matches"] == ["07_OUTPUTS/demo.txt"]

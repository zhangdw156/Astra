from __future__ import annotations

from pathlib import Path, PurePosixPath


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {"files": dict(scenario.get("files", {}))}

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "list_dir":
            return self._list_dir(arguments)
        if tool_name == "read_file":
            return self._read_file(arguments)
        if tool_name == "write_file":
            return self._write_file(arguments)
        if tool_name == "search_files":
            return self._search_files(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {"files": dict(self.state.get("files", {}))}

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _list_dir(self, arguments: dict) -> dict:
        path = self._normalize_path(arguments["path"])
        children = set()
        for file_path in self.state["files"]:
            parts = PurePosixPath(file_path).parts
            if path == ".":
                if parts:
                    children.add(parts[0])
                continue
            prefix = PurePosixPath(path).parts
            if parts[: len(prefix)] == prefix and len(parts) > len(prefix):
                children.add(parts[len(prefix)])
        return {"path": path, "entries": sorted(children)}

    def _read_file(self, arguments: dict) -> dict:
        path = self._normalize_path(arguments["path"])
        return {"path": path, "content": self.state["files"][path]}

    def _write_file(self, arguments: dict) -> dict:
        path = self._normalize_path(arguments["path"])
        content = str(arguments["content"])
        self.state["files"][path] = content
        return {"path": path, "bytes_written": len(content)}

    def _search_files(self, arguments: dict) -> dict:
        pattern = str(arguments["pattern"]).lower()
        matches = [
            path for path in sorted(self.state["files"]) if pattern in PurePosixPath(path).name.lower()
        ]
        return {"pattern": pattern, "matches": matches}

    def _normalize_path(self, raw_path: str) -> str:
        path = str(raw_path).strip() or "."
        normalized = str(PurePosixPath(path))
        if normalized.startswith("../") or normalized == "..":
            raise ValueError("Path escapes workspace")
        return "." if normalized == "" else normalized

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
        if tool_name == "grep":
            return self._grep(arguments)
        if tool_name == "glob":
            return self._glob(arguments)
        if tool_name == "tree":
            return self._tree(arguments)
        if tool_name == "check":
            return {"ripgrep": True, "fd": True, "tree": True}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {"files": dict(self.state["files"])}

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _grep(self, arguments: dict) -> dict:
        pattern = str(arguments["pattern"]).lower()
        limit = int(arguments.get("max", 100))
        file_type = str(arguments.get("type", "")).strip()
        results = []
        for path, content in sorted(self.state["files"].items()):
            if file_type and not path.endswith(f".{file_type}"):
                continue
            for line_no, line in enumerate(content.splitlines(), start=1):
                if pattern in line.lower():
                    results.append({"path": path, "line": line_no, "text": line})
                    if len(results) >= limit:
                        return {"results": results, "truncated": True}
        return {"results": results, "truncated": False}

    def _glob(self, arguments: dict) -> dict:
        token = str(arguments["pattern"]).replace("*", "").lower()
        kind = str(arguments.get("type", "f"))
        if kind == "d":
            seen = set()
            for path in self.state["files"]:
                for parent in PurePosixPath(path).parents:
                    if str(parent) != ".":
                        seen.add(str(parent))
            candidates = sorted(seen)
        else:
            candidates = sorted(self.state["files"])
        return {
            "matches": [
                candidate
                for candidate in candidates
                if token in PurePosixPath(candidate).name.lower()
            ]
        }

    def _tree(self, arguments: dict) -> dict:
        depth = int(arguments.get("depth", 3))
        nodes = []
        for path in sorted(self.state["files"]):
            if len(PurePosixPath(path).parts) <= depth:
                nodes.append(path)
        return {"nodes": nodes}

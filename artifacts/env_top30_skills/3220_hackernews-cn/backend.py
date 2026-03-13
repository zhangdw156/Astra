from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {"stories": [dict(story) for story in scenario.get("stories", [])]}

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name in {"top", "new", "best", "ask", "show", "jobs", "launch"}:
            return self._list(tool_name, arguments)
        if tool_name == "search":
            query = str(arguments["query"]).lower()
            matches = [
                story for story in self.state["stories"] if query in story["title"].lower()
            ]
            return {"results": matches}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return dict(self.state)

    def visible_state(self) -> dict:
        return dict(self.state)

    def _list(self, category: str, arguments: dict) -> dict:
        limit = int(arguments.get("limit", 10))
        stories = list(self.state["stories"])
        if category in {"top", "best"}:
            stories.sort(key=lambda story: story["score"], reverse=True)
        elif category != "new":
            stories = [story for story in stories if story["type"] == category]
        return {"stories": stories[:limit]}

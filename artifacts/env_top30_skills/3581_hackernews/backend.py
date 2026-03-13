from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "stories": [dict(story) for story in scenario.get("stories", [])],
            "users": dict(scenario.get("users", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name in {"top", "new", "best", "ask", "show", "jobs"}:
            return self._list(tool_name, arguments)
        if tool_name == "item":
            return self._item(arguments)
        if tool_name == "comments":
            return self._comments(arguments)
        if tool_name == "user":
            return {"user": dict(self.state["users"][str(arguments["username"])])}
        if tool_name == "search":
            return self._search(arguments)
        if tool_name == "whoishiring":
            return self._list("jobs", arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return dict(self.state)

    def visible_state(self) -> dict:
        return dict(self.state)

    def _list(self, category: str, arguments: dict) -> dict:
        limit = int(arguments.get("limit", 10))
        stories = list(self.state["stories"])
        if category == "top":
            stories.sort(key=lambda story: story["score"], reverse=True)
        elif category == "best":
            stories.sort(key=lambda story: story["score"], reverse=True)
        elif category != "new":
            stories = [story for story in stories if story["type"] == category]
        return {"stories": [self._summary(story) for story in stories[:limit]]}

    def _item(self, arguments: dict) -> dict:
        story = self._story(arguments["id"])
        return {"item": dict(story)}

    def _comments(self, arguments: dict) -> dict:
        story = self._story(arguments["id"])
        limit = int(arguments.get("limit", 10))
        return {"comments": story.get("comments", [])[:limit]}

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        limit = int(arguments.get("limit", 10))
        matches = [
            self._summary(story)
            for story in self.state["stories"]
            if query in story["title"].lower() or query in story["text"].lower()
        ]
        return {"results": matches[:limit]}

    def _story(self, item_id: int) -> dict:
        target = int(item_id)
        for story in self.state["stories"]:
            if story["id"] == target:
                return story
        raise ValueError(f"Unknown story id: {item_id}")

    def _summary(self, story: dict) -> dict:
        return {
            "id": story["id"],
            "title": story["title"],
            "score": story["score"],
            "by": story["by"],
            "type": story["type"],
        }

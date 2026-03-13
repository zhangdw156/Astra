from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "memories": [dict(memory) for memory in scenario.get("memories", [])],
            "next_id": int(scenario.get("next_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "memory_search":
            return self._search(arguments)
        if tool_name == "memory_get":
            return self._get(arguments)
        if tool_name == "memory_delete":
            return self._delete(arguments)
        if tool_name == "memory_stats":
            return self._stats()
        if tool_name == "memory_health":
            return {"status": "healthy", "version": "program-direct"}
        if tool_name == "memory_timeline":
            return self._timeline(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {"memories": [dict(memory) for memory in self.state["memories"]], "next_id": self.state["next_id"]}

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        type_filter = str(arguments.get("type", "")).lower()
        limit = int(arguments.get("limit", 10))
        matches = []
        for memory in self.state["memories"]:
            if query not in memory["text"].lower():
                continue
            if type_filter and memory["type"].lower() != type_filter:
                continue
            matches.append(dict(memory))
        return {"results": matches[:limit]}

    def _get(self, arguments: dict) -> dict:
        memory_id = int(arguments["id"])
        for memory in self.state["memories"]:
            if memory["id"] == memory_id:
                return {"memory": dict(memory)}
        raise ValueError(f"Unknown memory id: {memory_id}")

    def _delete(self, arguments: dict) -> dict:
        memory_id = int(arguments["id"])
        before = len(self.state["memories"])
        self.state["memories"] = [
            memory for memory in self.state["memories"] if memory["id"] != memory_id
        ]
        return {"deleted": len(self.state["memories"]) < before, "id": memory_id}

    def _stats(self) -> dict:
        counts: dict[str, int] = {}
        for memory in self.state["memories"]:
            counts[memory["type"]] = counts.get(memory["type"], 0) + 1
        return {"count": len(self.state["memories"]), "types": counts}

    def _timeline(self, arguments: dict) -> dict:
        memory_id = int(arguments["id"])
        ids = [memory["id"] for memory in self.state["memories"]]
        index = ids.index(memory_id)
        start = max(0, index - 1)
        end = min(len(ids), index + 2)
        return {"timeline": [dict(memory) for memory in self.state["memories"][start:end]]}

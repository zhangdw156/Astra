from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "default_user": scenario.get("default_user", "demo"),
            "memories": [dict(memory) for memory in scenario.get("memories", [])],
            "next_id": int(scenario.get("next_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "search_memories":
            return self._search(arguments)
        if tool_name == "add_memory":
            return self._add(arguments, conversation_context)
        if tool_name == "list_memories":
            return self._list(arguments)
        if tool_name == "delete_memory":
            return self._delete(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "default_user": self.state["default_user"],
            "memories": [dict(memory) for memory in self.state["memories"]],
            "next_id": self.state["next_id"],
        }

    def visible_state(self) -> dict:
        return {"memories": [dict(memory) for memory in self.state["memories"]]}

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        limit = int(arguments.get("limit", 3))
        user = str(arguments.get("user", self.state["default_user"]))
        scored = []
        for memory in self.state["memories"]:
            if memory["user"] != user:
                continue
            score = sum(token in memory["text"].lower() for token in query.split())
            if score > 0:
                scored.append((score, memory))
        scored.sort(key=lambda item: item[0], reverse=True)
        return {"results": [dict(memory) for _, memory in scored[:limit]]}

    def _add(self, arguments: dict, conversation_context: str | None) -> dict:
        user = str(arguments.get("user", self.state["default_user"]))
        text = str(arguments.get("text", "")).strip()
        if not text and isinstance(arguments.get("messages"), list):
            text = self._synthesize_from_messages(arguments["messages"], conversation_context)
        memory = {"id": f"m{self.state['next_id']}", "user": user, "text": text}
        self.state["next_id"] += 1
        self.state["memories"].append(memory)
        return {"memory": dict(memory)}

    def _list(self, arguments: dict) -> dict:
        user = str(arguments.get("user", self.state["default_user"]))
        memories = [dict(memory) for memory in self.state["memories"] if memory["user"] == user]
        return {"memories": memories}

    def _delete(self, arguments: dict) -> dict:
        user = str(arguments.get("user", self.state["default_user"]))
        if arguments.get("all"):
            before = len(self.state["memories"])
            self.state["memories"] = [
                memory for memory in self.state["memories"] if memory["user"] != user
            ]
            return {"deleted_count": before - len(self.state["memories"])}

        memory_id = str(arguments.get("memory_id", ""))
        before = len(self.state["memories"])
        self.state["memories"] = [
            memory for memory in self.state["memories"] if memory["id"] != memory_id
        ]
        return {"deleted": len(self.state["memories"]) < before, "memory_id": memory_id}

    def _synthesize_from_messages(self, messages: list, conversation_context: str | None) -> str:
        user_messages = [
            str(item.get("content", "")).strip()
            for item in messages
            if isinstance(item, dict) and item.get("role") == "user"
        ]
        seed = " ".join(part for part in user_messages if part)
        if conversation_context:
            seed = f"{seed} {conversation_context}".strip()
        return seed[:200]

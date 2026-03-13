from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "entities": {
                key: {
                    "facts": [dict(fact) for fact in value.get("facts", [])],
                    "summary": value.get("summary", ""),
                }
                for key, value in scenario.get("entities", {}).items()
            },
            "next_fact_id": int(scenario.get("next_fact_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "add_fact":
            return self._add_fact(arguments)
        if tool_name == "supersede_fact":
            return self._supersede_fact(arguments)
        if tool_name == "summarize_entity":
            return self._summarize_entity(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "entities": {
                key: {
                    "facts": [dict(fact) for fact in value["facts"]],
                    "summary": value["summary"],
                }
                for key, value in self.state["entities"].items()
            },
            "next_fact_id": self.state["next_fact_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _add_fact(self, arguments: dict) -> dict:
        entity = str(arguments["entity"])
        bucket = self.state["entities"].setdefault(entity, {"facts": [], "summary": ""})
        fact_id = self._next_fact_id(entity)
        fact = {
            "id": fact_id,
            "category": str(arguments["category"]),
            "fact": str(arguments["fact"]),
            "source": str(arguments.get("source", "conversation")),
            "status": "active",
        }
        bucket["facts"].append(fact)
        return {"entity": entity, "fact": fact}

    def _supersede_fact(self, arguments: dict) -> dict:
        entity = str(arguments["entity"])
        bucket = self.state["entities"].setdefault(entity, {"facts": [], "summary": ""})
        old_id = str(arguments["old"])
        for fact in bucket["facts"]:
            if fact["id"] == old_id:
                fact["status"] = "superseded"
        new_fact = self._add_fact(arguments)
        for fact in bucket["facts"]:
            if fact["id"] == old_id:
                fact["supersededBy"] = new_fact["fact"]["id"]
        return {"old": old_id, "new": new_fact["fact"]}

    def _summarize_entity(self, arguments: dict) -> dict:
        entity = str(arguments["entity"])
        bucket = self.state["entities"].setdefault(entity, {"facts": [], "summary": ""})
        active_facts = [fact["fact"] for fact in bucket["facts"] if fact["status"] == "active"]
        summary = "\n".join(f"- {fact}" for fact in active_facts)
        bucket["summary"] = summary
        return {"entity": entity, "summary": summary}

    def _next_fact_id(self, entity: str) -> str:
        slug = entity.split("/")[-1]
        fact_id = f"{slug}-{self.state['next_fact_id']:03d}"
        self.state["next_fact_id"] += 1
        return fact_id

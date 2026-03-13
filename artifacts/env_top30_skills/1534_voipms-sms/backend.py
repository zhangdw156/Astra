from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "today": str(scenario.get("today", "2026-03-13")),
            "owned_dids": list(scenario.get("owned_dids", [])),
            "messages": [dict(message) for message in scenario.get("messages", [])],
            "next_id": int(scenario.get("next_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "send_sms":
            return self._send_sms(arguments)
        if tool_name == "get_sms":
            return self._get_sms(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "today": self.state["today"],
            "owned_dids": list(self.state["owned_dids"]),
            "messages": [dict(message) for message in self.state["messages"]],
            "next_id": self.state["next_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _send_sms(self, arguments: dict) -> dict:
        did = str(arguments["did"])
        if did not in self.state["owned_dids"]:
            raise ValueError(f"Unknown DID: {did}")

        message = {
            "id": f"sms_{self.state['next_id']}",
            "did": did,
            "dst": str(arguments["dst"]),
            "direction": "outbound",
            "message": str(arguments["message"]),
            "timestamp": f"{self.state['today']}T12:00:00Z",
        }
        self.state["next_id"] += 1
        self.state["messages"].append(message)
        return {"message": dict(message), "status": "queued"}

    def _get_sms(self, arguments: dict) -> dict:
        did = arguments.get("did")
        days = int(arguments.get("days", 1))
        if days < 1:
            raise ValueError("days must be at least 1")

        today = datetime.fromisoformat(f"{self.state['today']}T00:00:00")
        start = today - timedelta(days=days)
        messages = []
        for message in self.state["messages"]:
            sent_at = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00")).replace(
                tzinfo=None
            )
            if sent_at < start:
                continue
            if did and message["did"] != str(did):
                continue
            messages.append(dict(message))
        messages.sort(key=lambda item: item["timestamp"], reverse=True)
        return {"messages": messages}

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        owned_dids = [self._normalize_phone(value) for value in scenario.get("owned_dids", [])]
        primary_did = self._normalize_phone(
            scenario.get("primary_did", owned_dids[0] if owned_dids else "")
        )
        self.state = {
            "today": str(scenario.get("today", "2026-03-13")),
            "primary_did": primary_did,
            "owned_dids": owned_dids,
            "messages": [self._normalize_message(message) for message in scenario.get("messages", [])],
            "next_id": int(scenario.get("next_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "list_dids":
            return self._list_dids()
        if tool_name == "send_sms":
            return self._send_sms(arguments)
        if tool_name == "get_sms":
            return self._get_sms(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "today": self.state["today"],
            "primary_did": self.state["primary_did"],
            "owned_dids": list(self.state["owned_dids"]),
            "messages": [dict(message) for message in self.state["messages"]],
            "next_id": self.state["next_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _list_dids(self) -> dict:
        return {
            "owned_dids": list(self.state["owned_dids"]),
            "primary_did": self.state["primary_did"],
        }

    def _send_sms(self, arguments: dict) -> dict:
        did = self._normalize_phone(arguments["did"])
        if did not in self.state["owned_dids"]:
            raise ValueError(f"Unknown DID: {did}")
        dst = self._normalize_phone(arguments["dst"])
        if not dst:
            raise ValueError("Destination phone number is required")
        if dst == did:
            raise ValueError("Destination number cannot be the same as the source DID")

        message = {
            "id": f"sms_{self.state['next_id']}",
            "did": did,
            "dst": dst,
            "direction": "outbound",
            "message": str(arguments["message"]),
            "timestamp": f"{self.state['today']}T12:00:00Z",
        }
        self.state["next_id"] += 1
        self.state["messages"].append(message)
        return {"message": dict(message), "status": "queued"}

    def _get_sms(self, arguments: dict) -> dict:
        did = arguments.get("did")
        normalized_did = self._normalize_phone(did) if did else None
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
            if normalized_did and message["did"] != normalized_did:
                continue
            messages.append(dict(message))
        messages.sort(key=lambda item: item["timestamp"], reverse=True)
        return {"messages": messages}

    def _normalize_message(self, message: dict) -> dict:
        normalized = dict(message)
        normalized["did"] = self._normalize_phone(normalized.get("did", ""))
        normalized["dst"] = self._normalize_phone(normalized.get("dst", ""))
        return normalized

    def _normalize_phone(self, value: object) -> str:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if len(digits) == 11 and digits.startswith("1"):
            return digits
        if len(digits) == 10:
            return f"1{digits}"
        return digits

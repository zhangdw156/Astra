from __future__ import annotations

import json
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "account_id": str(scenario.get("account_id", "acct_demo")),
            "balance": dict(scenario.get("balance", {"currency": "USD", "available_credit": 0.0})),
            "numbers": [dict(item) for item in scenario.get("numbers", [])],
            "available_numbers": list(scenario.get("available_numbers", [])),
            "connections": [dict(item) for item in scenario.get("connections", [])],
            "messages": [dict(item) for item in scenario.get("messages", [])],
            "calls": [dict(item) for item in scenario.get("calls", [])],
            "faxes": [dict(item) for item in scenario.get("faxes", [])],
            "next_ids": dict(scenario.get("next_ids", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "send_message":
            return self._send_message(arguments)
        if tool_name == "list_messages":
            return self._list_messages(arguments)
        if tool_name == "create_call":
            return self._create_call(arguments)
        if tool_name == "list_calls":
            return self._list_calls()
        if tool_name == "get_call":
            return self._get_call(arguments)
        if tool_name == "hangup_call":
            return self._hangup_call(arguments)
        if tool_name == "list_numbers":
            return self._list_numbers(arguments)
        if tool_name == "search_numbers":
            return self._search_numbers(arguments)
        if tool_name == "order_number":
            return self._order_number(arguments)
        if tool_name == "list_connections":
            return self._list_connections()
        if tool_name == "create_connection":
            return self._create_connection(arguments)
        if tool_name == "send_fax":
            return self._send_fax(arguments)
        if tool_name == "list_faxes":
            return self._list_faxes()
        if tool_name == "get_balance":
            return {"balance": dict(self.state["balance"])}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "account_id": self.state["account_id"],
            "balance": dict(self.state["balance"]),
            "numbers": [dict(item) for item in self.state["numbers"]],
            "available_numbers": list(self.state["available_numbers"]),
            "connections": [dict(item) for item in self.state["connections"]],
            "messages": [dict(item) for item in self.state["messages"]],
            "calls": [dict(item) for item in self.state["calls"]],
            "faxes": [dict(item) for item in self.state["faxes"]],
            "next_ids": dict(self.state["next_ids"]),
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _send_message(self, arguments: dict) -> dict:
        from_number = str(arguments["from"])
        self._assert_owned_number(from_number)
        message = {
            "id": self._next_id("message", "msg"),
            "from": from_number,
            "to": str(arguments["to"]),
            "text": str(arguments["text"]),
            "direction": "outbound",
            "status": "queued",
        }
        self.state["messages"].append(message)
        return {"data": dict(message)}

    def _list_messages(self, arguments: dict) -> dict:
        limit = int(arguments.get("page_size", 25))
        return {"data": [dict(item) for item in self.state["messages"][:limit]]}

    def _create_call(self, arguments: dict) -> dict:
        from_number = str(arguments["from"])
        self._assert_owned_number(from_number)
        connection_id = str(arguments["connection_id"])
        self._require_connection(connection_id)
        call = {
            "id": self._next_id("call", "call"),
            "from": from_number,
            "to": str(arguments["to"]),
            "connection_id": connection_id,
            "status": "active",
        }
        self.state["calls"].append(call)
        return {"data": dict(call)}

    def _list_calls(self) -> dict:
        return {"data": [dict(item) for item in self.state["calls"]]}

    def _get_call(self, arguments: dict) -> dict:
        call_id = str(arguments["id"])
        for call in self.state["calls"]:
            if call["id"] == call_id:
                return {"data": dict(call)}
        raise ValueError(f"Unknown call id: {call_id}")

    def _hangup_call(self, arguments: dict) -> dict:
        call_id = str(arguments["id"])
        for call in self.state["calls"]:
            if call["id"] == call_id:
                call["status"] = "completed"
                return {"data": dict(call)}
        raise ValueError(f"Unknown call id: {call_id}")

    def _list_numbers(self, arguments: dict) -> dict:
        limit = int(arguments.get("page_size", 25))
        return {"data": [dict(item) for item in self.state["numbers"][:limit]]}

    def _search_numbers(self, arguments: dict) -> dict:
        limit = int(arguments.get("limit", 10))
        country_code = str(arguments.get("country_code", "US"))
        del country_code
        matches = [{"phone_number": phone_number, "status": "available"} for phone_number in self.state["available_numbers"][:limit]]
        return {"data": matches}

    def _order_number(self, arguments: dict) -> dict:
        requested = json.loads(str(arguments["phone_numbers"]))
        if not isinstance(requested, list):
            raise ValueError("phone_numbers must decode to a list")

        ordered = []
        for phone_number in requested:
            value = str(phone_number)
            if value not in self.state["available_numbers"]:
                raise ValueError(f"Phone number not available: {value}")
            self.state["available_numbers"].remove(value)
            record = {"phone_number": value, "status": "active"}
            self.state["numbers"].append(record)
            ordered.append(record)
        return {"data": ordered}

    def _list_connections(self) -> dict:
        return {"data": [dict(item) for item in self.state["connections"]]}

    def _create_connection(self, arguments: dict) -> dict:
        connection = {
            "id": self._next_id("connection", "conn"),
            "name": str(arguments["name"]),
            "connection_type": str(arguments.get("connection_type", "ip")),
        }
        self.state["connections"].append(connection)
        return {"data": dict(connection)}

    def _send_fax(self, arguments: dict) -> dict:
        from_number = str(arguments["from"])
        self._assert_owned_number(from_number)
        fax = {
            "id": self._next_id("fax", "fax"),
            "from": from_number,
            "to": str(arguments["to"]),
            "media_url": str(arguments["media_url"]),
            "status": "queued",
        }
        self.state["faxes"].append(fax)
        return {"data": dict(fax)}

    def _list_faxes(self) -> dict:
        return {"data": [dict(item) for item in self.state["faxes"]]}

    def _next_id(self, key: str, prefix: str) -> str:
        current = int(self.state["next_ids"].get(key, 1))
        self.state["next_ids"][key] = current + 1
        return f"{prefix}_{current}"

    def _assert_owned_number(self, phone_number: str) -> None:
        owned = {item["phone_number"] for item in self.state["numbers"]}
        if phone_number not in owned:
            raise ValueError(f"Unknown Telnyx number: {phone_number}")

    def _require_connection(self, connection_id: str) -> None:
        for connection in self.state["connections"]:
            if connection["id"] == connection_id:
                return
        raise ValueError(f"Unknown connection id: {connection_id}")

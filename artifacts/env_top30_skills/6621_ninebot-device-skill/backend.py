from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "users": dict(scenario.get("users", {})),
            "sessions": dict(scenario.get("sessions", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "ninebot_login":
            return self._login(arguments)
        if tool_name == "ninebot_list_devices":
            return self._list_devices(arguments)
        if tool_name == "ninebot_get_device_info":
            return self._get_device_info(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {"users": dict(self.state["users"]), "sessions": dict(self.state["sessions"])}

    def visible_state(self) -> dict:
        return {"sessions": dict(self.state["sessions"])}

    def _login(self, arguments: dict) -> dict:
        username = str(arguments["username"])
        password = str(arguments["password"])
        user = self.state["users"].get(username)
        success = bool(user and user["password"] == password)
        token = f"token-{username}" if success else ""
        if success:
            self.state["sessions"][token] = username
        return {"success": success, "token": token}

    def _list_devices(self, arguments: dict) -> dict:
        user = self._require_token(arguments["token"])
        devices = [
            {"sn": device["sn"], "name": device["name"]}
            for device in self.state["users"][user]["devices"]
        ]
        return {"devices": devices, "lang": str(arguments.get("lang", "zh"))}

    def _get_device_info(self, arguments: dict) -> dict:
        user = self._require_token(arguments["token"])
        sn = str(arguments["sn"])
        for device in self.state["users"][user]["devices"]:
            if device["sn"] == sn:
                return dict(device)
        raise ValueError(f"Unknown device SN: {sn}")

    def _require_token(self, token: str) -> str:
        value = str(token)
        if value not in self.state["sessions"]:
            raise ValueError("Invalid token")
        return self.state["sessions"][value]

from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {"flights": [dict(item) for item in scenario.get("flights", [])]}

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name != "flight_search":
            raise ValueError(f"Unsupported tool: {tool_name}")
        date = str(arguments["departure_date"])
        departure = str(arguments["departure_city"])
        destination = str(arguments["destination_city"])
        matches = [
            {
                "耗时": item["duration"],
                "航班号": item["flight_no"],
                "到达时间": item["arrival_time"],
                "出发机场": item["departure_airport"],
                "价格": item["price"],
                "餐食": item["meal"],
                "机型": item["aircraft"],
                "出发时间": item["departure_time"],
                "目的机场": item["destination_airport"],
            }
            for item in self.state["flights"]
            if item["departure_date"] == date
            and item["departure_city"] == departure
            and item["destination_city"] == destination
        ]
        matches.sort(key=lambda item: item["价格"])
        return {"code": 0, "data": matches, "message": "success"}

    def snapshot_state(self) -> dict:
        return {"flights": [dict(item) for item in self.state["flights"]]}

    def visible_state(self) -> dict:
        return self.snapshot_state()

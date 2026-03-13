from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "places": [dict(item) for item in scenario.get("places", [])],
            "departures": {
                key: [dict(dep) for dep in value]
                for key, value in scenario.get("departures", {}).items()
            },
            "trips": [self._copy_trip(item) for item in scenario.get("trips", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "search":
            query = str(arguments["query"]).lower()
            matches = [
                self._present_place(place)
                for place in self.state["places"]
                if query in place["name"].lower() or query in place["label"].lower()
            ]
            return {"results": matches}
        if tool_name == "trip":
            return self._trip(arguments)
        if tool_name == "departures":
            stop_id = str(arguments["stop_id"])
            limit = int(arguments.get("limit", 10))
            return {
                "stop": self._place_by_id(stop_id)["name"],
                "id": stop_id,
                "departures": [dict(item) for item in self.state["departures"].get(stop_id, [])[:limit]],
            }
        if tool_name == "stop":
            return self._present_stop(self._place_by_id(str(arguments["stop_id"])))
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "places": [dict(item) for item in self.state["places"]],
            "departures": {
                key: [dict(dep) for dep in value]
                for key, value in self.state["departures"].items()
            },
            "trips": [self._copy_trip(item) for item in self.state["trips"]],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _trip(self, arguments: dict) -> dict:
        from_place = self._resolve_place(str(arguments["from_place"]))
        to_place = self._resolve_place(str(arguments["to"]))
        modes = self._parse_modes(arguments.get("modes"))
        matches = []
        for trip in self.state["trips"]:
            if trip["from_id"] != from_place["id"] or trip["to_id"] != to_place["id"]:
                continue
            if modes and not set(modes).issubset(set(trip["modes"])):
                continue
            matches.extend([dict(item) for item in trip["patterns"]])
        return {"trips": matches}

    def _resolve_place(self, raw: str) -> dict:
        value = str(raw)
        if value.startswith("NSR:"):
            return self._place_by_id(value)
        lowered = value.lower()
        for place in self.state["places"]:
            if lowered in place["name"].lower() or lowered in place["label"].lower():
                return place
        raise ValueError(f"Unknown place: {raw}")

    def _parse_modes(self, raw_modes: object) -> list[str]:
        if raw_modes is None or str(raw_modes).strip() == "":
            return []
        return [item.strip() for item in str(raw_modes).split(",") if item.strip()]

    def _place_by_id(self, stop_id: str) -> dict:
        for place in self.state["places"]:
            if place["id"] == stop_id:
                return place
        raise ValueError(f"Unknown stop id: {stop_id}")

    def _present_place(self, place: dict) -> dict:
        return {
            "id": place["id"],
            "name": place["name"],
            "label": place["label"],
            "county": place.get("county"),
            "locality": place.get("locality"),
            "coordinates": dict(place["coordinates"]),
        }

    def _present_stop(self, place: dict) -> dict:
        return {
            "id": place["id"],
            "name": place["name"],
            "latitude": place["coordinates"]["lat"],
            "longitude": place["coordinates"]["lon"],
            "quays": [dict(item) for item in place.get("quays", [])],
        }

    def _copy_trip(self, trip: dict) -> dict:
        return {
            "from_id": trip["from_id"],
            "to_id": trip["to_id"],
            "modes": list(trip.get("modes", [])),
            "patterns": [
                {
                    "depart": pattern["depart"],
                    "arrive": pattern["arrive"],
                    "duration_sec": pattern["duration_sec"],
                    "walk_m": pattern["walk_m"],
                    "legs": [dict(leg) for leg in pattern.get("legs", [])],
                }
                for pattern in trip.get("patterns", [])
            ],
        }

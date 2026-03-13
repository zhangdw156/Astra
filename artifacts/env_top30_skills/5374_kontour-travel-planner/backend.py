from __future__ import annotations

import json
import re
from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.destinations = self._load_reference_json("destinations.json")
        self.benchmarks = self._load_reference_json("budget-benchmarks.json")
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "saved_itineraries": dict(scenario.get("saved_itineraries", {})),
            "planned_trips": [dict(item) for item in scenario.get("planned_trips", [])],
            "exports": [dict(item) for item in scenario.get("exports", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "plan_trip":
            return self._plan_trip(arguments, conversation_context)
        if tool_name == "export_gmaps":
            return self._export_gmaps(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "saved_itineraries": dict(self.state["saved_itineraries"]),
            "planned_trips": [dict(item) for item in self.state["planned_trips"]],
            "exports": [dict(item) for item in self.state["exports"]],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _plan_trip(self, arguments: dict, conversation_context: str | None) -> dict:
        query = str(arguments["query"])
        destination = self._extract_destination(query)
        duration = self._extract_duration_days(query)
        travelers = self._extract_travelers(query)
        budget_tier = self._extract_budget_tier(query)
        interests = self._extract_interests(query)
        accommodation = self._extract_accommodation(query)
        transport = self._extract_transport(query)
        constraints = self._extract_constraints(query)

        trip_context: dict = {}
        if destination:
            trip_context["destination"] = destination
        if duration is not None:
            trip_context["duration"] = duration
        if travelers is not None:
            trip_context["travelers"] = {"adults": travelers}
        if budget_tier:
            trip_context["budget"] = self._budget_info(destination, budget_tier, duration, travelers)
        if interests:
            trip_context["interests"] = interests
        if accommodation:
            trip_context["accommodation"] = accommodation
        if transport:
            trip_context["transport"] = transport
        if constraints:
            trip_context["constraints"] = constraints

        progress = self._compute_progress(trip_context)
        stage = self._stage_from_progress(progress)
        open_dimensions = self._open_dimensions(trip_context)
        conflicts = self._detect_conflicts(trip_context)

        result = {
            "trip_context": trip_context,
            "progress_percent": progress,
            "planning_stage": stage,
            "open_dimensions": open_dimensions,
            "conflicts": conflicts,
            "summary": self._summarize_trip(trip_context, stage, conversation_context),
            "recommended_next_question": self._next_question(trip_context, open_dimensions),
        }
        self.state["planned_trips"].append(
            {
                "query": query,
                "trip_context": trip_context,
                "planning_stage": stage,
                "progress_percent": progress,
            }
        )
        return result

    def _export_gmaps(self, arguments: dict) -> dict:
        itinerary_file = str(arguments["itinerary_file"])
        export_kml = bool(arguments.get("export_kml", False))
        itinerary = self.state["saved_itineraries"].get(itinerary_file)
        if itinerary is None:
            raise ValueError(f"Unknown itinerary file: {itinerary_file}")

        day_routes = []
        all_points: list[str] = []
        for day in itinerary.get("days", []):
            coords = [f"{item['lat']},{item['lng']}" for item in day.get("locations", [])]
            if not coords:
                continue
            all_points.extend(coords)
            day_routes.append(
                {
                    "day": day["day"],
                    "url": f"https://www.google.com/maps/dir/{'/'.join(coords)}",
                }
            )

        export = {
            "itinerary_file": itinerary_file,
            "trip_url": f"https://www.google.com/maps/dir/{'/'.join(all_points)}" if all_points else "",
            "day_routes": day_routes,
            "kml_file": f"{itinerary_file}.kml" if export_kml else None,
        }
        self.state["exports"].append(export)
        return export

    def _extract_destination(self, query: str) -> dict | None:
        lowered = query.lower()
        for item in self.destinations:
            if item["name"].lower() in lowered or item["country"].lower() in lowered:
                return {
                    "name": item["name"],
                    "country": item["country"],
                    "coordinates": list(item["coordinates"]),
                    "currency": item["currency"],
                    "timezone": item["timezone"],
                }
        return None

    def _extract_duration_days(self, query: str) -> int | None:
        match = re.search(r"(\d+)\s*(day|days|night|nights|week|weeks)", query, re.IGNORECASE)
        if not match:
            return None
        value = int(match.group(1))
        if "week" in match.group(2).lower():
            return value * 7
        return value

    def _extract_travelers(self, query: str) -> int | None:
        lowered = query.lower()
        if "couple" in lowered:
            return 2
        if "solo" in lowered:
            return 1
        if "family" in lowered:
            return 4
        match = re.search(r"(\d+)\s*(people|travelers|adults|persons)", lowered)
        if match:
            return int(match.group(1))
        return None

    def _extract_budget_tier(self, query: str) -> str:
        lowered = query.lower()
        if re.search(r"mid.range|mid-range|moderate|comfort", lowered):
            return "mid"
        if re.search(r"budget|cheap|backpack", lowered):
            return "budget"
        if re.search(r"luxury|premium|high.end|splurge", lowered):
            return "luxury"
        return ""

    def _extract_interests(self, query: str) -> list[str]:
        keywords = [
            "food",
            "temples",
            "culture",
            "history",
            "museum",
            "art",
            "beach",
            "adventure",
            "hiking",
            "nature",
            "nightlife",
            "shopping",
            "wellness",
        ]
        lowered = query.lower()
        return [item for item in keywords if item in lowered]

    def _extract_accommodation(self, query: str) -> str:
        lowered = query.lower()
        for keyword in ("hotel", "hostel", "resort", "apartment", "boutique"):
            if keyword in lowered:
                return keyword
        return ""

    def _extract_transport(self, query: str) -> list[str]:
        lowered = query.lower()
        found = []
        for keyword in ("flights", "flight", "trains", "train", "rental car", "metro", "public transit"):
            if keyword in lowered:
                found.append(keyword.replace(" ", "-"))
        return found

    def _extract_constraints(self, query: str) -> list[str]:
        lowered = query.lower()
        constraints = []
        if "vegetarian" in lowered:
            constraints.append("vegetarian")
        if "accessibility" in lowered:
            constraints.append("accessibility")
        if "slow pace" in lowered:
            constraints.append("slow pace")
        return constraints

    def _budget_info(
        self,
        destination: dict | None,
        budget_tier: str,
        duration: int | None,
        travelers: int | None,
    ) -> dict:
        budget = {"tier": budget_tier}
        if destination and duration and travelers:
            matched = next(
                (
                    item
                    for item in self.destinations
                    if item["name"] == destination["name"] and item["country"] == destination["country"]
                ),
                None,
            )
            if matched:
                daily = matched["avg_daily_cost_usd"].get(budget_tier)
                if daily is not None:
                    budget["daily_per_person"] = daily
                    budget["estimated_total"] = daily * duration * travelers
        return budget

    def _compute_progress(self, trip_context: dict) -> int:
        score = 0
        weights = {
            "destination": 15,
            "duration": 10,
            "travelers": 10,
            "budget": 15,
            "interests": 10,
            "accommodation": 10,
            "transport": 5,
            "constraints": 5,
        }
        for key, weight in weights.items():
            value = trip_context.get(key)
            if value:
                score += weight
        return score

    def _stage_from_progress(self, progress: int) -> str:
        if progress >= 85:
            return "confirm"
        if progress >= 60:
            return "refine"
        if progress >= 30:
            return "develop"
        return "discover"

    def _open_dimensions(self, trip_context: dict) -> list[str]:
        order = [
            "destination",
            "dates",
            "duration",
            "travelers",
            "budget",
            "interests",
            "accommodation",
            "transport",
            "constraints",
        ]
        present = set(trip_context)
        open_dims = []
        for item in order:
            if item == "dates":
                if "dates" not in present:
                    open_dims.append(item)
            elif item not in present:
                open_dims.append(item)
        return open_dims

    def _detect_conflicts(self, trip_context: dict) -> list[str]:
        conflicts = []
        destination = trip_context.get("destination")
        budget = trip_context.get("budget", {})
        if destination and budget.get("tier") == "budget":
            matched = next(
                (
                    item
                    for item in self.destinations
                    if item["name"] == destination["name"] and item["country"] == destination["country"]
                ),
                None,
            )
            if matched and matched["avg_daily_cost_usd"]["budget"] >= 90:
                conflicts.append("Budget tier may be unrealistic for destination costs.")
        return conflicts

    def _summarize_trip(
        self,
        trip_context: dict,
        stage: str,
        conversation_context: str | None,
    ) -> str:
        if not trip_context.get("destination"):
            return "The trip brief is still early; destination and core logistics need to be clarified."
        parts = [
            f"{trip_context['destination']['name']} is the current target",
            f"planning is in the {stage} stage",
        ]
        if trip_context.get("duration"):
            parts.append(f"for {trip_context['duration']} days")
        if trip_context.get("budget", {}).get("tier"):
            parts.append(f"with a {trip_context['budget']['tier']} budget")
        if trip_context.get("interests"):
            parts.append(f"focused on {', '.join(trip_context['interests'][:3])}")
        text = ", ".join(parts) + "."
        if conversation_context:
            text += f" Context: {conversation_context[:80]}"
        return text

    def _next_question(self, trip_context: dict, open_dimensions: list[str]) -> str:
        if not open_dimensions:
            return "Do you want me to turn this into a day-by-day itinerary next?"
        dimension = open_dimensions[0]
        prompts = {
            "destination": "Which destination should we prioritize first?",
            "dates": "What travel window works best for this trip?",
            "duration": "How many days should I optimize for?",
            "travelers": "How many people are traveling?",
            "budget": "What budget range should I optimize for?",
            "interests": "What are your top must-do experiences?",
            "accommodation": "What type of stay fits you best?",
            "transport": "Should I optimize around flights, trains, or local transit?",
            "constraints": "Any dietary, accessibility, or pace constraints I should honor?",
        }
        return prompts[dimension]

    def _load_reference_json(self, filename: str):
        path = self.skill_dir / "references" / filename
        return json.loads(path.read_text(encoding="utf-8"))

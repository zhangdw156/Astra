from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "services": [dict(item) for item in scenario.get("services", [])],
            "oncalls": [dict(item) for item in scenario.get("oncalls", [])],
            "incidents": [self._copy_incident(item) for item in scenario.get("incidents", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "pd_incidents":
            return self._incidents()
        if tool_name == "pd_incident_detail":
            return self._incident_detail(arguments)
        if tool_name == "pd_oncall":
            return {"oncalls": [dict(item) for item in self.state["oncalls"]]}
        if tool_name == "pd_services":
            return self._services()
        if tool_name == "pd_recent":
            return self._recent(arguments)
        if tool_name == "pd_incident_ack":
            return self._write_incident(arguments, target_status="acknowledged")
        if tool_name == "pd_incident_resolve":
            return self._write_incident(arguments, target_status="resolved")
        if tool_name == "pd_incident_note":
            return self._incident_note(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "services": [dict(item) for item in self.state["services"]],
            "oncalls": [dict(item) for item in self.state["oncalls"]],
            "incidents": [self._copy_incident(item) for item in self.state["incidents"]],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _incidents(self) -> dict:
        incidents = [item for item in self.state["incidents"] if item["status"] in {"triggered", "acknowledged"}]
        incidents.sort(key=lambda item: (item["urgency"] != "high", item["status"] != "triggered"))
        return {"total_incidents": len(incidents), "incidents": [self._incident_summary(item) for item in incidents]}

    def _incident_detail(self, arguments: dict) -> dict:
        incident = self._incident_by_id(str(arguments["incident_id"]))
        return {
            "incident": self._incident_summary(incident),
            "timeline": [dict(item) for item in incident["timeline"]],
            "alerts": [dict(item) for item in incident["alerts"]],
            "notes": [dict(item) for item in incident["notes"]],
            "analysis": {
                "alert_count": incident["alert_count"],
                "acknowledged": incident["status"] == "acknowledged",
                "trigger_source": incident["alerts"][0]["source"] if incident["alerts"] else None,
            },
        }

    def _services(self) -> dict:
        services = [dict(item) for item in self.state["services"]]
        return {"services": services}

    def _recent(self, arguments: dict) -> dict:
        service_id = str(arguments.get("service", "")).strip()
        incidents = list(self.state["incidents"])
        if service_id:
            incidents = [item for item in incidents if item["service_id"] == service_id]
        stats = {
            "total": len(incidents),
            "by_status": self._count_by(incidents, "status"),
            "by_urgency": self._count_by(incidents, "urgency"),
        }
        return {"incidents": [self._incident_summary(item) for item in incidents], "stats": stats}

    def _write_incident(self, arguments: dict, *, target_status: str) -> dict:
        incident = self._incident_by_id(str(arguments["incident_id"]))
        if not bool(arguments.get("confirm", False)):
            return {"would_update": True, "incident_id": incident["id"], "target_status": target_status}
        incident["status"] = target_status
        incident["last_status_change"] = "2026-03-13T10:00:00Z"
        incident["timeline"].append(
            {
                "type": f"{target_status}_log_entry",
                "created_at": incident["last_status_change"],
                "summary": f"Incident {target_status}",
            }
        )
        return {"incident": self._incident_summary(incident)}

    def _incident_note(self, arguments: dict) -> dict:
        incident = self._incident_by_id(str(arguments["incident_id"]))
        if not bool(arguments.get("confirm", False)):
            return {"would_add_note": True, "incident_id": incident["id"]}
        note = {
            "content": str(arguments["content"]),
            "created_at": "2026-03-13T10:05:00Z",
        }
        incident["notes"].append(note)
        return {"note": dict(note), "incident_id": incident["id"]}

    def _count_by(self, incidents: list[dict], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for incident in incidents:
            value = str(incident.get(key, "unknown"))
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _incident_summary(self, incident: dict) -> dict:
        service = self._service_by_id(incident["service_id"])
        return {
            "id": incident["id"],
            "incident_number": incident["incident_number"],
            "title": incident["title"],
            "status": incident["status"],
            "urgency": incident["urgency"],
            "service": {"id": service["id"], "name": service["name"]},
            "created_at": incident["created_at"],
            "assignments": [dict(item) for item in incident["assignments"]],
            "alert_count": incident["alert_count"],
            "escalation_level": incident["escalation_level"],
            "last_status_change": incident["last_status_change"],
        }

    def _incident_by_id(self, incident_id: str) -> dict:
        for incident in self.state["incidents"]:
            if incident["id"] == incident_id:
                return incident
        raise ValueError(f"Unknown incident id: {incident_id}")

    def _service_by_id(self, service_id: str) -> dict:
        for service in self.state["services"]:
            if service["id"] == service_id:
                return service
        raise ValueError(f"Unknown service id: {service_id}")

    def _copy_incident(self, incident: dict) -> dict:
        return {
            "id": incident["id"],
            "incident_number": incident["incident_number"],
            "title": incident["title"],
            "status": incident["status"],
            "urgency": incident["urgency"],
            "service_id": incident["service_id"],
            "created_at": incident["created_at"],
            "last_status_change": incident["last_status_change"],
            "assignments": [dict(item) for item in incident.get("assignments", [])],
            "alert_count": incident["alert_count"],
            "escalation_level": incident["escalation_level"],
            "timeline": [dict(item) for item in incident.get("timeline", [])],
            "alerts": [dict(item) for item in incident.get("alerts", [])],
            "notes": [dict(item) for item in incident.get("notes", [])],
        }

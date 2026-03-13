from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "issues": [dict(issue) for issue in scenario.get("issues", [])],
            "slas": [dict(sla) for sla in scenario.get("slas", [])],
            "warranty_claims": [dict(claim) for claim in scenario.get("warranty_claims", [])],
            "maintenance_schedules": [dict(item) for item in scenario.get("maintenance_schedules", [])],
            "maintenance_visits": [dict(item) for item in scenario.get("maintenance_visits", [])],
            "next_issue_id": int(scenario.get("next_issue_id", 1)),
            "next_sla_id": int(scenario.get("next_sla_id", 1)),
            "next_warranty_id": int(scenario.get("next_warranty_id", 1)),
            "next_schedule_id": int(scenario.get("next_schedule_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        handlers = {
            "add_issue": self._add_issue,
            "update_issue": self._update_issue,
            "get_issue": self._get_issue,
            "list_issues": self._list_issues,
            "add_issue_comment": self._add_issue_comment,
            "resolve_issue": self._resolve_issue,
            "reopen_issue": self._reopen_issue,
            "add_sla": self._add_sla,
            "list_slas": self._list_slas,
            "add_warranty_claim": self._add_warranty_claim,
            "update_warranty_claim": self._update_warranty_claim,
            "list_warranty_claims": self._list_warranty_claims,
            "add_maintenance_schedule": self._add_maintenance_schedule,
            "list_maintenance_schedules": self._list_maintenance_schedules,
            "record_maintenance_visit": self._record_maintenance_visit,
            "sla_compliance_report": self._sla_compliance_report,
            "overdue_issues_report": self._overdue_issues_report,
            "status": self._status,
        }
        return handlers[tool_name](arguments)

    def snapshot_state(self) -> dict:
        return dict(self.state)

    def visible_state(self) -> dict:
        return dict(self.state)

    def _add_issue(self, arguments: dict) -> dict:
        issue = {
            "issue_id": f"ISS-{self.state['next_issue_id']:04d}",
            "subject": str(arguments["subject"]),
            "status": "open",
            "priority": str(arguments.get("priority", "medium")),
            "issue_type": str(arguments.get("issue_type", "question")),
            "description": str(arguments.get("description", "")),
            "assigned_to": str(arguments.get("assigned_to", "")),
            "comments": [],
        }
        self.state["next_issue_id"] += 1
        self.state["issues"].append(issue)
        return dict(issue)

    def _update_issue(self, arguments: dict) -> dict:
        issue = self._find_by_key(self.state["issues"], "issue_id", arguments["issue_id"])
        for key in ("status", "priority", "assigned_to", "issue_type", "description"):
            if key in arguments:
                issue[key] = str(arguments[key])
        return dict(issue)

    def _get_issue(self, arguments: dict) -> dict:
        return dict(self._find_by_key(self.state["issues"], "issue_id", arguments["issue_id"]))

    def _list_issues(self, arguments: dict) -> dict:
        issues = list(self.state["issues"])
        for key in ("status", "priority", "customer_id", "assigned_to", "company_id"):
            if key in arguments:
                issues = [issue for issue in issues if issue.get(key) == arguments[key]]
        return {"issues": [dict(issue) for issue in issues]}

    def _add_issue_comment(self, arguments: dict) -> dict:
        issue = self._find_by_key(self.state["issues"], "issue_id", arguments["issue_id"])
        comment = {
            "comment": str(arguments["comment"]),
            "comment_by": str(arguments.get("comment_by", "employee")),
            "is_internal": int(arguments.get("is_internal", 0)),
        }
        issue["comments"].append(comment)
        return {"issue_id": issue["issue_id"], "comment": comment}

    def _resolve_issue(self, arguments: dict) -> dict:
        issue = self._find_by_key(self.state["issues"], "issue_id", arguments["issue_id"])
        issue["status"] = "resolved"
        issue["resolution_notes"] = str(arguments.get("resolution_notes", ""))
        return dict(issue)

    def _reopen_issue(self, arguments: dict) -> dict:
        issue = self._find_by_key(self.state["issues"], "issue_id", arguments["issue_id"])
        issue["status"] = "open"
        issue["reopen_reason"] = str(arguments.get("reason", ""))
        return dict(issue)

    def _add_sla(self, arguments: dict) -> dict:
        sla = {
            "sla_id": f"SLA-{self.state['next_sla_id']:03d}",
            "name": str(arguments["name"]),
            "priorities": str(arguments["priorities"]),
            "is_default": str(arguments.get("is_default", "0")) == "1",
        }
        self.state["next_sla_id"] += 1
        self.state["slas"].append(sla)
        return dict(sla)

    def _list_slas(self, arguments: dict) -> dict:
        del arguments
        return {"slas": [dict(sla) for sla in self.state["slas"]]}

    def _add_warranty_claim(self, arguments: dict) -> dict:
        claim = {
            "warranty_claim_id": f"WAR-{self.state['next_warranty_id']:04d}",
            "customer_id": str(arguments["customer_id"]),
            "complaint_description": str(arguments["complaint_description"]),
            "status": "pending",
        }
        self.state["next_warranty_id"] += 1
        self.state["warranty_claims"].append(claim)
        return dict(claim)

    def _update_warranty_claim(self, arguments: dict) -> dict:
        claim = self._find_by_key(
            self.state["warranty_claims"],
            "warranty_claim_id",
            arguments["warranty_claim_id"],
        )
        for key in ("status", "resolution", "resolution_date", "cost"):
            if key in arguments:
                claim[key] = str(arguments[key])
        return dict(claim)

    def _list_warranty_claims(self, arguments: dict) -> dict:
        claims = list(self.state["warranty_claims"])
        for key in ("customer_id", "status"):
            if key in arguments:
                claims = [claim for claim in claims if claim.get(key) == arguments[key]]
        return {"warranty_claims": [dict(claim) for claim in claims]}

    def _add_maintenance_schedule(self, arguments: dict) -> dict:
        schedule = {
            "schedule_id": f"MS-{self.state['next_schedule_id']:04d}",
            "customer_id": str(arguments["customer_id"]),
            "start_date": str(arguments["start_date"]),
            "end_date": str(arguments["end_date"]),
            "status": "scheduled",
        }
        self.state["next_schedule_id"] += 1
        self.state["maintenance_schedules"].append(schedule)
        return dict(schedule)

    def _list_maintenance_schedules(self, arguments: dict) -> dict:
        schedules = list(self.state["maintenance_schedules"])
        for key in ("customer_id", "item_id", "status"):
            if key in arguments:
                schedules = [item for item in schedules if item.get(key) == arguments[key]]
        return {"maintenance_schedules": [dict(item) for item in schedules]}

    def _record_maintenance_visit(self, arguments: dict) -> dict:
        visit = {
            "schedule_id": str(arguments["schedule_id"]),
            "visit_date": str(arguments["visit_date"]),
            "status": str(arguments.get("status", "completed")),
        }
        self.state["maintenance_visits"].append(visit)
        schedule = self._find_by_key(
            self.state["maintenance_schedules"], "schedule_id", arguments["schedule_id"]
        )
        schedule["status"] = "completed"
        return dict(visit)

    def _sla_compliance_report(self, arguments: dict) -> dict:
        del arguments
        resolved = len([issue for issue in self.state["issues"] if issue["status"] == "resolved"])
        total = len(self.state["issues"])
        return {"total_issues": total, "resolved_issues": resolved}

    def _overdue_issues_report(self, arguments: dict) -> dict:
        del arguments
        overdue = [issue for issue in self.state["issues"] if issue["status"] not in {"resolved", "closed"}]
        return {"overdue_issues": [dict(issue) for issue in overdue]}

    def _status(self, arguments: dict) -> dict:
        del arguments
        open_issues = len([issue for issue in self.state["issues"] if issue["status"] == "open"])
        overdue = len(self._overdue_issues_report({})["overdue_issues"])
        return {
            "open_issues": open_issues,
            "sla_count": len(self.state["slas"]),
            "overdue_issues": overdue,
        }

    def _find_by_key(self, rows: list[dict], key: str, value: str) -> dict:
        target = str(value)
        for row in rows:
            if row.get(key) == target:
                return row
        raise ValueError(f"Unknown {key}: {value}")

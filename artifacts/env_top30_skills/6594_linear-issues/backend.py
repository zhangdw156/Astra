from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "current_user_id": str(scenario.get("current_user_id", "")),
            "teams": [dict(item) for item in scenario.get("teams", [])],
            "states": [dict(item) for item in scenario.get("states", [])],
            "users": [dict(item) for item in scenario.get("users", [])],
            "issues": [self._copy_issue(item) for item in scenario.get("issues", [])],
            "next_issue_numbers": dict(scenario.get("next_issue_numbers", {})),
            "next_comment_id": int(scenario.get("next_comment_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "list_my_issues":
            issues = [item for item in self.state["issues"] if item.get("assignee_id") == self.state["current_user_id"]]
            return {"issues": [self._present_issue(item) for item in issues]}
        if tool_name == "list_team_issues":
            team_id = str(arguments["team_id"])
            issues = [item for item in self.state["issues"] if item["team_id"] == team_id]
            return {"issues": [self._present_issue(item) for item in issues]}
        if tool_name == "get_issue":
            return {"issue": self._present_issue(self._issue_by_id(str(arguments["issue_id"])), include_comments=True)}
        if tool_name == "search_issues":
            query = str(arguments["query"]).lower()
            matches = [
                self._present_issue(item)
                for item in self.state["issues"]
                if query in item["title"].lower() or query in item["description"].lower()
            ]
            return {"issues": matches}
        if tool_name == "create_issue":
            return {"issue": self._create_issue(arguments)}
        if tool_name == "update_issue":
            return {"issue": self._update_issue(arguments)}
        if tool_name == "add_comment":
            return {"comment": self._add_comment(arguments)}
        if tool_name == "list_teams":
            return {"teams": [dict(item) for item in self.state["teams"]]}
        if tool_name == "list_states":
            team_id = str(arguments.get("team_id", "")).strip()
            states = self.state["states"] if not team_id else [item for item in self.state["states"] if item["team_id"] == team_id]
            return {"states": [dict(item) for item in states]}
        if tool_name == "list_users":
            return {"users": [dict(item) for item in self.state["users"]]}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "current_user_id": self.state["current_user_id"],
            "teams": [dict(item) for item in self.state["teams"]],
            "states": [dict(item) for item in self.state["states"]],
            "users": [dict(item) for item in self.state["users"]],
            "issues": [self._copy_issue(item) for item in self.state["issues"]],
            "next_issue_numbers": dict(self.state["next_issue_numbers"]),
            "next_comment_id": self.state["next_comment_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _create_issue(self, arguments: dict) -> dict:
        team = self._team_by_id(str(arguments["team_id"]))
        identifier = f"{team['key']}-{self.state['next_issue_numbers'][team['key']]}"
        self.state["next_issue_numbers"][team["key"]] += 1
        issue = {
            "id": identifier,
            "team_id": team["id"],
            "title": str(arguments["title"]),
            "description": str(arguments.get("description", "")),
            "priority": int(arguments.get("priority", 0)),
            "state_id": str(arguments.get("state_id", self._default_state_for_team(team["id"])["id"])),
            "assignee_id": str(arguments.get("assignee_id", "")) or None,
            "comments": [],
        }
        self.state["issues"].append(issue)
        return self._present_issue(issue, include_comments=True)

    def _update_issue(self, arguments: dict) -> dict:
        issue = self._issue_by_id(str(arguments["issue_id"]))
        for field in ("title", "description", "state_id", "assignee_id", "priority"):
            if field in arguments and arguments[field] is not None:
                if field == "priority":
                    issue[field] = int(arguments[field])
                else:
                    issue[field] = str(arguments[field])
        return self._present_issue(issue, include_comments=True)

    def _add_comment(self, arguments: dict) -> dict:
        issue = self._issue_by_id(str(arguments["issue_id"]))
        comment = {
            "id": f"comment_{self.state['next_comment_id']}",
            "body": str(arguments["body"]),
            "user_id": self.state["current_user_id"],
        }
        self.state["next_comment_id"] += 1
        issue["comments"].append(comment)
        return dict(comment)

    def _team_by_id(self, team_id: str) -> dict:
        for team in self.state["teams"]:
            if team["id"] == team_id:
                return team
        raise ValueError(f"Unknown team id: {team_id}")

    def _default_state_for_team(self, team_id: str) -> dict:
        for state in self.state["states"]:
            if state["team_id"] == team_id:
                return state
        raise ValueError(f"No states for team id: {team_id}")

    def _issue_by_id(self, issue_id: str) -> dict:
        for issue in self.state["issues"]:
            if issue["id"] == issue_id:
                return issue
        raise ValueError(f"Unknown issue id: {issue_id}")

    def _state_by_id(self, state_id: str) -> dict:
        for state in self.state["states"]:
            if state["id"] == state_id:
                return state
        raise ValueError(f"Unknown state id: {state_id}")

    def _user_by_id(self, user_id: str | None) -> dict | None:
        if not user_id:
            return None
        for user in self.state["users"]:
            if user["id"] == user_id:
                return user
        raise ValueError(f"Unknown user id: {user_id}")

    def _present_issue(self, issue: dict, *, include_comments: bool = False) -> dict:
        team = self._team_by_id(issue["team_id"])
        state = self._state_by_id(issue["state_id"])
        assignee = self._user_by_id(issue.get("assignee_id"))
        rendered = {
            "id": issue["id"],
            "identifier": issue["id"],
            "title": issue["title"],
            "description": issue["description"],
            "priority": issue["priority"],
            "team": dict(team),
            "state": dict(state),
            "assignee": dict(assignee) if assignee else None,
        }
        if include_comments:
            rendered["comments"] = [dict(item) for item in issue["comments"]]
        return rendered

    def _copy_issue(self, issue: dict) -> dict:
        return {
            "id": issue["id"],
            "team_id": issue["team_id"],
            "title": issue["title"],
            "description": issue.get("description", ""),
            "priority": int(issue.get("priority", 0)),
            "state_id": issue["state_id"],
            "assignee_id": issue.get("assignee_id"),
            "comments": [dict(item) for item in issue.get("comments", [])],
        }

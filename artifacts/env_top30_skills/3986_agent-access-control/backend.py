from __future__ import annotations

from pathlib import Path


class SkillBackend:
    RATE_LIMITS = {
        0: {"hour": 1, "day": 3},
        1: {"hour": 20, "day": 100},
        2: {"hour": 50, "day": 500},
        3: {"hour": 999999, "day": 999999},
    }

    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "ownerIds": list(scenario.get("ownerIds", [])),
            "blockedIds": list(scenario.get("blockedIds", [])),
            "approvedContacts": dict(scenario.get("approvedContacts", {})),
            "pendingApprovals": dict(scenario.get("pendingApprovals", {})),
            "rateLimits": dict(scenario.get("rateLimits", {})),
            "logs": list(scenario.get("logs", [])),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        handlers = {
            "check_access_tier": self._check_access_tier,
            "handle_stranger": self._handle_stranger,
            "approve_contact": self._approve_contact,
            "enforce_tier": self._enforce_tier,
            "normalize_id": self._normalize_id,
            "check_rate_limit": self._check_rate_limit,
            "log_event": self._log_event,
            "init_access_control": self._init_access_control,
        }
        return handlers[tool_name](arguments)

    def snapshot_state(self) -> dict:
        return {
            "ownerIds": list(self.state["ownerIds"]),
            "blockedIds": list(self.state["blockedIds"]),
            "approvedContacts": dict(self.state["approvedContacts"]),
            "pendingApprovals": dict(self.state["pendingApprovals"]),
            "rateLimits": dict(self.state["rateLimits"]),
            "logs": list(self.state["logs"]),
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _check_access_tier(self, arguments: dict) -> dict:
        sender_id = str(arguments["senderId"])
        if sender_id in self.state["ownerIds"]:
            tier = 3
        elif sender_id in self.state["blockedIds"]:
            tier = 0
        else:
            tier = int(self.state["approvedContacts"].get(sender_id, 0))
        return {"senderId": sender_id, "tier": tier}

    def _handle_stranger(self, arguments: dict) -> dict:
        sender_id = str(arguments["senderId"])
        self.state["pendingApprovals"][sender_id] = {
            "platform": str(arguments["platform"]),
            "message": str(arguments["message"])[:100],
        }
        self._log_event(
            {
                "action": "deflected",
                "senderId": sender_id,
                "platform": str(arguments["platform"]),
                "message": str(arguments["message"])[:50],
            }
        )
        return {"senderId": sender_id, "status": "pending_approval", "reply": "NO_REPLY"}

    def _approve_contact(self, arguments: dict) -> dict:
        sender_id = str(arguments["senderId"])
        response = str(arguments["ownerResponse"]).lower()
        if response in {"approve", "yes", "trusted"}:
            self.state["approvedContacts"][sender_id] = 2
            action = "approved"
        elif response in {"chat", "chat-only", "chat only"}:
            self.state["approvedContacts"][sender_id] = 1
            action = "approved"
        elif response in {"block", "no", "deny"}:
            self.state["blockedIds"].append(sender_id)
            action = "blocked"
        else:
            action = "ignored"
        self.state["pendingApprovals"].pop(sender_id, None)
        self._log_event(
            {
                "action": action,
                "senderId": sender_id,
                "platform": "telegram",
                "message": response,
            }
        )
        return {"senderId": sender_id, "action": action}

    def _enforce_tier(self, arguments: dict) -> dict:
        tier = int(arguments["tier"])
        action = str(arguments["requestedAction"]).lower()
        allowed = tier == 2 and any(x in action for x in ["search", "weather", "time"])
        if tier == 1:
            allowed = False
        return {"tier": tier, "requestedAction": action, "allowed": allowed}

    def _normalize_id(self, arguments: dict) -> dict:
        platform = str(arguments["platform"])
        raw = str(arguments["rawId"]).strip()
        normalized = raw
        if platform in {"telegram", "discord"} and ":" not in raw:
            normalized = f"{platform}:{raw}"
        elif platform in {"whatsapp", "signal", "imessage"}:
            normalized = "".join(ch for ch in raw if ch.isdigit() or ch == "+")
        return {"normalized_id": normalized}

    def _check_rate_limit(self, arguments: dict) -> dict:
        sender_id = str(arguments["senderId"])
        tier = int(arguments["tier"])
        limits = self.RATE_LIMITS[tier]
        current = self.state["rateLimits"].get(sender_id, {"hour": 0, "day": 0})
        current["hour"] += 1
        current["day"] += 1
        self.state["rateLimits"][sender_id] = current
        allowed = current["hour"] <= limits["hour"] and current["day"] <= limits["day"]
        if not allowed:
            self._log_event(
                {
                    "action": "rate_limited",
                    "senderId": sender_id,
                    "platform": "telegram",
                    "message": "",
                }
            )
        return {"senderId": sender_id, "allowed": allowed, "counts": current}

    def _log_event(self, arguments: dict) -> dict:
        event = {
            "action": str(arguments["action"]),
            "senderId": str(arguments["senderId"]),
            "platform": str(arguments["platform"]),
            "message": str(arguments.get("message", "")),
        }
        self.state["logs"].append(event)
        self.state["logs"] = self.state["logs"][-100:]
        return {"logged": True, "event": event}

    def _init_access_control(self, arguments: dict) -> dict:
        agent_name = str(arguments.get("agentName", "Assistant"))
        self.state.setdefault("agentName", agent_name)
        return {"initialized": True, "agentName": agent_name}

from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "current_agent_id": str(scenario.get("current_agent_id", "")),
            "profiles": {key: dict(value) for key, value in scenario.get("profiles", {}).items()},
            "xeets": [dict(item) for item in scenario.get("xeets", [])],
            "notifications": [dict(item) for item in scenario.get("notifications", [])],
            "conversations": [self._copy_conversation(item) for item in scenario.get("conversations", [])],
            "bookmarks": list(scenario.get("bookmarks", [])),
            "lists": [dict(item) for item in scenario.get("lists", [])],
            "models": list(scenario.get("models", [])),
            "settings": dict(scenario.get("settings", {})),
            "next_ids": dict(scenario.get("next_ids", {})),
            "deactivated": False,
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if self.state.get("deactivated") and tool_name != "agentx_register":
            raise ValueError("Account is deactivated")

        if tool_name == "agentx_register":
            return self._register(arguments)
        if tool_name == "agentx_post_xeet":
            return self._post_xeet(arguments)
        if tool_name == "agentx_timeline":
            return self._timeline(arguments)
        if tool_name == "agentx_profile":
            return self._profile(arguments)
        if tool_name == "agentx_agents":
            return self._agents(arguments)
        if tool_name == "agentx_follow":
            return self._follow(arguments)
        if tool_name == "agentx_block":
            return self._block(arguments)
        if tool_name == "agentx_xeet":
            return self._xeet(arguments)
        if tool_name == "agentx_search":
            return self._search(arguments)
        if tool_name == "agentx_suggestions":
            return self._suggestions(arguments)
        if tool_name == "agentx_notifications":
            return self._notifications(arguments)
        if tool_name == "agentx_messages":
            return self._messages(arguments)
        if tool_name == "agentx_bookmarks":
            return self._bookmarks(arguments)
        if tool_name == "agentx_lists":
            return self._lists(arguments)
        if tool_name == "agentx_models":
            return {"models": list(self.state["models"])}
        if tool_name == "agentx_pin":
            return self._pin(arguments)
        if tool_name == "agentx_settings":
            return self._settings(arguments)
        if tool_name == "agentx_deactivate":
            self.state["deactivated"] = True
            return {"deactivated": True}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "current_agent_id": self.state["current_agent_id"],
            "profiles": {key: dict(value) for key, value in self.state["profiles"].items()},
            "xeets": [dict(item) for item in self.state["xeets"]],
            "notifications": [dict(item) for item in self.state["notifications"]],
            "conversations": [self._copy_conversation(item) for item in self.state["conversations"]],
            "bookmarks": list(self.state["bookmarks"]),
            "lists": [dict(item) for item in self.state["lists"]],
            "models": list(self.state["models"]),
            "settings": dict(self.state["settings"]),
            "next_ids": dict(self.state["next_ids"]),
            "deactivated": self.state["deactivated"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _register(self, arguments: dict) -> dict:
        handle = str(arguments["handle"])
        if any(profile["handle"] == handle for profile in self.state["profiles"].values()):
            raise ValueError(f"Handle already exists: {handle}")
        if str(arguments["model"]) not in self.state["models"]:
            raise ValueError(f"Unknown model: {arguments['model']}")
        agent_id = self._next_id("agent", "agent")
        profile = {
            "id": agent_id,
            "handle": handle,
            "displayName": str(arguments["displayName"]),
            "model": str(arguments["model"]),
            "bio": str(arguments.get("bio", "")),
            "location": str(arguments.get("location", "")),
            "website": str(arguments.get("website", "")),
            "operator": dict(arguments.get("operator", {})) if isinstance(arguments.get("operator"), dict) else {},
            "followers": [],
            "following": [],
            "blocked": [],
            "muted": [],
            "pinned_xeet_id": None,
        }
        self.state["profiles"][agent_id] = profile
        self.state["current_agent_id"] = agent_id
        self.state["deactivated"] = False
        return {"agent": dict(profile), "apiKey": f"key_{agent_id}"}

    def _post_xeet(self, arguments: dict) -> dict:
        xeet = self._create_xeet(
            content=str(arguments["content"]),
            reply_to=self._optional_string(arguments.get("replyTo")),
            quote_of=None,
        )
        return {"xeet": xeet}

    def _timeline(self, arguments: dict) -> dict:
        limit = min(int(arguments.get("limit", 20)), 20)
        current = self._current_profile()
        followed = set(current.get("following", []))
        xeets = [item for item in self.state["xeets"] if item["author_id"] in followed]
        xeets.sort(key=lambda item: item["created_at"], reverse=True)
        return {"xeets": [dict(item) for item in xeets[:limit]], "nextCursor": None}

    def _profile(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        if action == "me":
            return {"profile": dict(self._current_profile())}
        if action == "by_handle":
            return {"profile": dict(self._profile_by_handle(str(arguments["handle"])))}
        if action == "update":
            profile = self._current_profile()
            for field in ("displayName", "bio", "location", "website", "avatarUrl", "bannerUrl"):
                if field in arguments and arguments[field] is not None:
                    profile[field] = str(arguments[field])
            return {"profile": dict(profile)}
        raise ValueError(f"Unsupported profile action: {action}")

    def _agents(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        profile = self._profile_by_handle(str(arguments["handle"]))
        limit = min(int(arguments.get("limit", 20)), 20)
        if action == "xeets":
            items = [dict(xeet) for xeet in self.state["xeets"] if xeet["author_id"] == profile["id"]]
            items.sort(key=lambda item: item["created_at"], reverse=True)
            return {"xeets": items[:limit]}
        if action == "followers":
            return {"agents": [dict(self.state["profiles"][agent_id]) for agent_id in profile["followers"][:limit]]}
        if action == "following":
            return {"agents": [dict(self.state["profiles"][agent_id]) for agent_id in profile["following"][:limit]]}
        raise ValueError(f"Unsupported agents action: {action}")

    def _follow(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        target = self._profile_by_handle(str(arguments["handle"]))
        current = self._current_profile()
        current_following = current["following"]
        target_followers = target["followers"]
        if action == "follow":
            if target["id"] not in current_following:
                current_following.append(target["id"])
            if current["id"] not in target_followers:
                target_followers.append(current["id"])
            return {"following": True, "handle": target["handle"]}
        if action == "unfollow":
            if target["id"] in current_following:
                current_following.remove(target["id"])
            if current["id"] in target_followers:
                target_followers.remove(current["id"])
            return {"following": False, "handle": target["handle"]}
        raise ValueError(f"Unsupported follow action: {action}")

    def _block(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        target = self._profile_by_handle(str(arguments["handle"]))
        current = self._current_profile()
        if action in {"block", "unblock"}:
            collection = current["blocked"]
        elif action in {"mute", "unmute"}:
            collection = current["muted"]
        else:
            raise ValueError(f"Unsupported block action: {action}")
        present = target["id"] in collection
        if action in {"block", "mute"} and not present:
            collection.append(target["id"])
            present = True
        if action in {"unblock", "unmute"} and present:
            collection.remove(target["id"])
            present = False
        return {"action": action, "handle": target["handle"], "active": present}

    def _xeet(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        xeet = self._xeet_by_id(str(arguments["xeetId"]))
        current_id = self.state["current_agent_id"]
        if action == "get":
            return {"xeet": dict(xeet)}
        if action == "delete":
            if xeet["author_id"] != current_id:
                raise ValueError("Can only delete your own xeet")
            self.state["xeets"] = [item for item in self.state["xeets"] if item["id"] != xeet["id"]]
            return {"deleted": True, "xeetId": xeet["id"]}
        if action == "like":
            if current_id not in xeet["likes"]:
                xeet["likes"].append(current_id)
            return {"xeet": dict(xeet)}
        if action == "unlike":
            if current_id in xeet["likes"]:
                xeet["likes"].remove(current_id)
            return {"xeet": dict(xeet)}
        if action == "rexeet":
            if current_id not in xeet["rexeets"]:
                xeet["rexeets"].append(current_id)
            return {"xeet": dict(xeet)}
        if action == "unrexeet":
            if current_id in xeet["rexeets"]:
                xeet["rexeets"].remove(current_id)
            return {"xeet": dict(xeet)}
        if action == "quote":
            quoted = self._create_xeet(content=str(arguments["content"]), reply_to=None, quote_of=xeet["id"])
            return {"xeet": quoted}
        if action == "replies":
            replies = [dict(item) for item in self.state["xeets"] if item.get("reply_to") == xeet["id"]]
            replies.sort(key=lambda item: item["created_at"], reverse=True)
            return {"xeets": replies}
        raise ValueError(f"Unsupported xeet action: {action}")

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        search_type = str(arguments["type"])
        if search_type == "xeets":
            xeets = [dict(item) for item in self.state["xeets"] if query in item["content"].lower()]
            xeets.sort(key=lambda item: item["created_at"], reverse=True)
            return {"xeets": xeets}
        if search_type == "agents":
            agents = [
                dict(profile)
                for profile in self.state["profiles"].values()
                if query in profile["handle"].lower() or query in profile["displayName"].lower()
            ]
            return {"agents": agents}
        raise ValueError(f"Unsupported search type: {search_type}")

    def _suggestions(self, arguments: dict) -> dict:
        limit = min(int(arguments.get("limit", 5)), 20)
        current = self._current_profile()
        excluded = set(current["following"]) | {current["id"]}
        agents = [dict(profile) for profile in self.state["profiles"].values() if profile["id"] not in excluded]
        agents.sort(key=lambda profile: profile["handle"])
        return {"agents": agents[:limit]}

    def _notifications(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        current_id = self.state["current_agent_id"]
        items = [item for item in self.state["notifications"] if item["agent_id"] == current_id]
        if action == "list":
            limit = min(int(arguments.get("limit", 20)), 20)
            return {"notifications": [dict(item) for item in items[:limit]]}
        if action == "mark_read":
            for item in items:
                item["read"] = True
            return {"marked_read": len(items)}
        raise ValueError(f"Unsupported notifications action: {action}")

    def _messages(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        current_id = self.state["current_agent_id"]
        if action == "list":
            conversations = [
                self._copy_conversation(item)
                for item in self.state["conversations"]
                if current_id in item["participants"]
            ]
            return {"conversations": conversations}
        if action == "get":
            conversation = self._conversation_by_id(str(arguments["conversationId"]))
            return {"conversation": self._copy_conversation(conversation)}
        if action == "send":
            recipient_id = str(arguments["recipientId"])
            content = str(arguments["content"])
            conversation = self._find_or_create_conversation(current_id, recipient_id)
            message = {
                "id": self._next_id("message", "dm"),
                "sender_id": current_id,
                "content": content,
            }
            conversation["messages"].append(message)
            return {"message": dict(message), "conversationId": conversation["id"]}
        raise ValueError(f"Unsupported messages action: {action}")

    def _bookmarks(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        xeet_id = self._optional_string(arguments.get("xeetId"))
        if action == "list":
            items = [dict(self._xeet_by_id(item)) for item in self.state["bookmarks"]]
            return {"xeets": items}
        if action == "add":
            target = self._xeet_by_id(str(xeet_id))
            if target["id"] not in self.state["bookmarks"]:
                self.state["bookmarks"].append(target["id"])
            return {"bookmarked": True, "xeetId": target["id"]}
        if action == "remove":
            if xeet_id in self.state["bookmarks"]:
                self.state["bookmarks"].remove(str(xeet_id))
            return {"bookmarked": False, "xeetId": xeet_id}
        raise ValueError(f"Unsupported bookmarks action: {action}")

    def _lists(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        current_id = self.state["current_agent_id"]
        if action == "list":
            lists = [dict(item) for item in self.state["lists"] if item["owner_id"] == current_id]
            return {"lists": lists}
        if action == "create":
            record = {
                "id": self._next_id("list", "list"),
                "owner_id": current_id,
                "name": str(arguments["name"]),
                "description": str(arguments.get("description", "")),
                "member_ids": [],
            }
            self.state["lists"].append(record)
            return {"list": dict(record)}
        target_list = self._list_by_id(str(arguments["listId"]))
        agent_id = self._optional_string(arguments.get("agentId"))
        if action == "add_member":
            if agent_id and agent_id not in target_list["member_ids"]:
                target_list["member_ids"].append(agent_id)
            return {"list": dict(target_list)}
        if action == "remove_member":
            if agent_id in target_list["member_ids"]:
                target_list["member_ids"].remove(agent_id)
            return {"list": dict(target_list)}
        if action == "timeline":
            member_ids = set(target_list["member_ids"])
            xeets = [dict(item) for item in self.state["xeets"] if item["author_id"] in member_ids]
            xeets.sort(key=lambda item: item["created_at"], reverse=True)
            return {"xeets": xeets}
        raise ValueError(f"Unsupported lists action: {action}")

    def _pin(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        profile = self._current_profile()
        if action == "pin":
            xeet = self._xeet_by_id(str(arguments["xeetId"]))
            profile["pinned_xeet_id"] = xeet["id"]
            return {"pinned": xeet["id"]}
        if action == "unpin":
            profile["pinned_xeet_id"] = None
            return {"pinned": None}
        raise ValueError(f"Unsupported pin action: {action}")

    def _settings(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        if action == "get":
            return {"settings": dict(self.state["settings"])}
        if action == "update":
            if isinstance(arguments.get("privacy"), dict):
                self.state["settings"]["privacy"] = dict(arguments["privacy"])
            if isinstance(arguments.get("notifications"), dict):
                self.state["settings"]["notifications"] = dict(arguments["notifications"])
            return {"settings": dict(self.state["settings"])}
        raise ValueError(f"Unsupported settings action: {action}")

    def _create_xeet(self, *, content: str, reply_to: str | None, quote_of: str | None) -> dict:
        text = str(content).strip()
        if not text:
            raise ValueError("content must not be empty")
        xeet = {
            "id": self._next_id("xeet", "xeet"),
            "author_id": self.state["current_agent_id"],
            "content": text,
            "reply_to": reply_to,
            "quote_of": quote_of,
            "likes": [],
            "rexeets": [],
            "created_at": f"2026-03-13T10:0{self.state['next_ids']['xeet'] - 1}Z",
        }
        self.state["xeets"].append(xeet)
        return dict(xeet)

    def _current_profile(self) -> dict:
        return self.state["profiles"][self.state["current_agent_id"]]

    def _profile_by_handle(self, handle: str) -> dict:
        for profile in self.state["profiles"].values():
            if profile["handle"] == handle:
                return profile
        raise ValueError(f"Unknown handle: {handle}")

    def _xeet_by_id(self, xeet_id: str) -> dict:
        for xeet in self.state["xeets"]:
            if xeet["id"] == xeet_id:
                return xeet
        raise ValueError(f"Unknown xeet id: {xeet_id}")

    def _conversation_by_id(self, conversation_id: str) -> dict:
        for conversation in self.state["conversations"]:
            if conversation["id"] == conversation_id:
                return conversation
        raise ValueError(f"Unknown conversation id: {conversation_id}")

    def _find_or_create_conversation(self, agent_a: str, agent_b: str) -> dict:
        participants = {agent_a, agent_b}
        for conversation in self.state["conversations"]:
            if set(conversation["participants"]) == participants:
                return conversation
        conversation = {
            "id": self._next_id("conversation", "conv"),
            "participants": [agent_a, agent_b],
            "messages": [],
        }
        self.state["conversations"].append(conversation)
        return conversation

    def _list_by_id(self, list_id: str) -> dict:
        for item in self.state["lists"]:
            if item["id"] == list_id:
                return item
        raise ValueError(f"Unknown list id: {list_id}")

    def _next_id(self, key: str, prefix: str) -> str:
        current = int(self.state["next_ids"].get(key, 1))
        self.state["next_ids"][key] = current + 1
        return f"{prefix}_{current}"

    def _optional_string(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _copy_conversation(self, conversation: dict) -> dict:
        return {
            "id": conversation["id"],
            "participants": list(conversation["participants"]),
            "messages": [dict(item) for item in conversation.get("messages", [])],
        }

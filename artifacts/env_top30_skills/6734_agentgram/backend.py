from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "platform": dict(scenario.get("platform", {})),
            "current_agent_id": str(scenario.get("current_agent_id", "")),
            "agents": {key: dict(value) for key, value in scenario.get("agents", {}).items()},
            "posts": [self._copy_post(item) for item in scenario.get("posts", [])],
            "stories": [dict(item) for item in scenario.get("stories", [])],
            "notifications": [dict(item) for item in scenario.get("notifications", [])],
            "next_ids": dict(scenario.get("next_ids", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "health":
            return {"healthy": bool(self.state["platform"].get("healthy", False))}
        if tool_name == "test":
            return {
                "healthy": bool(self.state["platform"].get("healthy", False)),
                "authenticated": bool(self.state["current_agent_id"]),
            }
        if tool_name == "register":
            return self._register(arguments)
        if tool_name == "me":
            return {"agent": dict(self._current_agent())}
        if tool_name == "status":
            return {"authenticated": bool(self.state["current_agent_id"]), "agent_id": self.state["current_agent_id"]}
        if tool_name == "feed":
            return self._feed(arguments)
        if tool_name == "get_post":
            return {"post": self._copy_post(self._post_by_id(str(arguments["post_id"])))}
        if tool_name == "comments":
            post = self._post_by_id(str(arguments["post_id"]))
            return {"comments": [dict(item) for item in post["comments"]]}
        if tool_name == "trending_tags":
            return self._trending_tags()
        if tool_name == "explore":
            return self._explore(arguments)
        if tool_name == "list_agents":
            return {"agents": [dict(agent) for agent in self.state["agents"].values()]}
        if tool_name == "create_post":
            return {"post": self._create_post(arguments)}
        if tool_name == "comment":
            return {"comment": self._comment(arguments)}
        if tool_name == "like":
            return {"post": self._like(arguments)}
        if tool_name == "follow":
            return self._follow(arguments)
        if tool_name == "repost":
            return {"repost": self._repost(arguments)}
        if tool_name == "story":
            return {"story": self._story(arguments)}
        if tool_name == "stories":
            return self._stories()
        if tool_name == "notifications":
            return {"notifications": [dict(item) for item in self._agent_notifications()]}
        if tool_name == "notifications_read":
            items = self._agent_notifications()
            for item in items:
                item["read"] = True
            return {"marked_read": len(items)}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "platform": dict(self.state["platform"]),
            "current_agent_id": self.state["current_agent_id"],
            "agents": {key: dict(value) for key, value in self.state["agents"].items()},
            "posts": [self._copy_post(item) for item in self.state["posts"]],
            "stories": [dict(item) for item in self.state["stories"]],
            "notifications": [dict(item) for item in self.state["notifications"]],
            "next_ids": dict(self.state["next_ids"]),
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _register(self, arguments: dict) -> dict:
        agent_id = self._next_id("agent", "ag")
        agent = {
            "id": agent_id,
            "name": str(arguments["name"]),
            "description": str(arguments.get("description", "")),
            "reputation": 0,
            "followers": [],
            "following": [],
        }
        self.state["agents"][agent_id] = agent
        self.state["current_agent_id"] = agent_id
        return {"agent": dict(agent), "apiKey": f"ag_key_{agent_id}"}

    def _feed(self, arguments: dict) -> dict:
        limit = min(int(arguments.get("limit", 10)), 50)
        sort = str(arguments.get("sort", "hot"))
        posts = list(self.state["posts"])
        if sort == "new":
            posts.sort(key=lambda item: item["created_at"], reverse=True)
        elif sort == "top":
            posts.sort(key=lambda item: item["score"], reverse=True)
        else:
            posts.sort(key=lambda item: (item["score"], item["created_at"]), reverse=True)
        return {"posts": [self._copy_post(item) for item in posts[:limit]]}

    def _trending_tags(self) -> dict:
        counts: dict[str, int] = {}
        for post in self.state["posts"]:
            for tag in post.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        tags = [{"tag": tag, "count": count} for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
        return {"tags": tags}

    def _explore(self, arguments: dict) -> dict:
        limit = min(int(arguments.get("limit", 20)), 50)
        posts = sorted(self.state["posts"], key=lambda item: item["score"], reverse=True)
        return {"posts": [self._copy_post(item) for item in posts[:limit]]}

    def _create_post(self, arguments: dict) -> dict:
        post = {
            "id": self._next_id("post", "post"),
            "author_id": self.state["current_agent_id"],
            "title": str(arguments["title"]),
            "content": str(arguments["content"]),
            "tags": self._extract_tags(str(arguments["content"])),
            "likes": [],
            "comments": [],
            "reposts": [],
            "score": 1,
            "created_at": f"2026-03-13T10:0{self.state['next_ids']['post'] - 1}Z",
        }
        self.state["posts"].append(post)
        return dict(post)

    def _comment(self, arguments: dict) -> dict:
        post = self._post_by_id(str(arguments["post_id"]))
        comment = {
            "id": self._next_id("comment", "comment"),
            "author_id": self.state["current_agent_id"],
            "content": str(arguments["content"]),
        }
        post["comments"].append(comment)
        post["score"] += 1
        self._add_notification(post["author_id"], "comment", post["id"])
        return dict(comment)

    def _like(self, arguments: dict) -> dict:
        post = self._post_by_id(str(arguments["post_id"]))
        current = self.state["current_agent_id"]
        if current in post["likes"]:
            post["likes"].remove(current)
            post["score"] = max(0, post["score"] - 1)
        else:
            post["likes"].append(current)
            post["score"] += 1
            self._add_notification(post["author_id"], "like", post["id"])
        return self._copy_post(post)

    def _follow(self, arguments: dict) -> dict:
        target = self._agent_by_id(str(arguments["agent_id"]))
        current = self._current_agent()
        following = current["following"]
        followers = target["followers"]
        active = target["id"] not in following
        if active:
            following.append(target["id"])
            if current["id"] not in followers:
                followers.append(current["id"])
            self._add_notification(target["id"], "follow", None)
        else:
            following.remove(target["id"])
            if current["id"] in followers:
                followers.remove(current["id"])
        return {"following": active, "agent_id": target["id"]}

    def _repost(self, arguments: dict) -> dict:
        post = self._post_by_id(str(arguments["post_id"]))
        record = {
            "agent_id": self.state["current_agent_id"],
            "comment": str(arguments.get("comment", "")),
        }
        post["reposts"].append(record)
        post["score"] += 1
        return dict(record)

    def _story(self, arguments: dict) -> dict:
        story = {
            "id": self._next_id("story", "story"),
            "author_id": self.state["current_agent_id"],
            "content": str(arguments["content"]),
            "created_at": f"2026-03-13T10:1{self.state['next_ids']['story'] - 1}Z",
        }
        self.state["stories"].append(story)
        return dict(story)

    def _stories(self) -> dict:
        following = set(self._current_agent()["following"])
        items = [dict(item) for item in self.state["stories"] if item["author_id"] in following]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return {"stories": items}

    def _agent_notifications(self) -> list[dict]:
        current = self.state["current_agent_id"]
        return [item for item in self.state["notifications"] if item["agent_id"] == current]

    def _add_notification(self, agent_id: str | None, kind: str, post_id: str | None) -> None:
        if not agent_id or agent_id == self.state["current_agent_id"]:
            return
        self.state["notifications"].append(
            {
                "id": self._next_id("notification", "notif"),
                "agent_id": agent_id,
                "type": kind,
                "post_id": post_id,
                "read": False,
            }
        )

    def _current_agent(self) -> dict:
        return self.state["agents"][self.state["current_agent_id"]]

    def _agent_by_id(self, agent_id: str) -> dict:
        if agent_id not in self.state["agents"]:
            raise ValueError(f"Unknown agent id: {agent_id}")
        return self.state["agents"][agent_id]

    def _post_by_id(self, post_id: str) -> dict:
        for post in self.state["posts"]:
            if post["id"] == post_id:
                return post
        raise ValueError(f"Unknown post id: {post_id}")

    def _next_id(self, key: str, prefix: str) -> str:
        current = int(self.state["next_ids"].get(key, 1))
        self.state["next_ids"][key] = current + 1
        return f"{prefix}_{current}"

    def _extract_tags(self, text: str) -> list[str]:
        return [token for token in text.split() if token.startswith("#")]

    def _copy_post(self, post: dict) -> dict:
        return {
            "id": post["id"],
            "author_id": post["author_id"],
            "title": post["title"],
            "content": post["content"],
            "tags": list(post.get("tags", [])),
            "likes": list(post.get("likes", [])),
            "comments": [dict(item) for item in post.get("comments", [])],
            "reposts": [dict(item) for item in post.get("reposts", [])],
            "score": post["score"],
            "created_at": post["created_at"],
        }

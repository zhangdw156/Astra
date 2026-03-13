from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "agent": dict(scenario.get("agent", {})),
            "following": list(scenario.get("following", [])),
            "agents": dict(scenario.get("agents", {})),
            "posts": [dict(post) for post in scenario.get("posts", [])],
            "notifications": [dict(item) for item in scenario.get("notifications", [])],
            "next_post_id": int(scenario.get("next_post_id", 1)),
            "next_notification_id": int(scenario.get("next_notification_id", 1)),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "moltx_status":
            return {"agent": dict(self.state["agent"])}
        if tool_name == "moltx_notifications":
            return {"notifications": [dict(item) for item in self.state["notifications"]]}
        if tool_name == "moltx_mentions":
            return {"posts": [dict(post) for post in self._mentions()]}
        if tool_name == "moltx_global":
            return self._global(arguments)
        if tool_name == "moltx_following":
            return {"posts": [dict(post) for post in self._following_posts()]}
        if tool_name == "moltx_post":
            return {"post": self._create_post(arguments["content"], post_type="post")}
        if tool_name == "moltx_reply":
            return {
                "post": self._create_post(
                    arguments["content"],
                    post_type="reply",
                    parent_id=str(arguments["parent_id"]),
                )
            }
        if tool_name == "moltx_quote":
            return {
                "post": self._create_post(
                    arguments["content"],
                    post_type="quote",
                    parent_id=str(arguments["parent_id"]),
                )
            }
        if tool_name == "moltx_like":
            return {"post": self._like_post(str(arguments["post_id"]))}
        if tool_name == "moltx_follow":
            return {"agent_name": self._follow_agent(str(arguments["agent_name"])), "following": True}
        if tool_name == "moltx_search":
            return self._search(arguments)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "agent": dict(self.state["agent"]),
            "following": list(self.state["following"]),
            "agents": dict(self.state["agents"]),
            "posts": [dict(post) for post in self.state["posts"]],
            "notifications": [dict(item) for item in self.state["notifications"]],
            "next_post_id": self.state["next_post_id"],
            "next_notification_id": self.state["next_notification_id"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _global(self, arguments: dict) -> dict:
        limit = int(arguments.get("limit", 20))
        posts = sorted(self.state["posts"], key=lambda post: post["created_at"], reverse=True)
        return {"posts": [dict(post) for post in posts[:limit]]}

    def _following_posts(self) -> list[dict]:
        followed = set(self.state["following"])
        posts = [post for post in self.state["posts"] if post["author"] in followed]
        posts.sort(key=lambda post: post["created_at"], reverse=True)
        return posts

    def _mentions(self) -> list[dict]:
        handle = self.state["agent"].get("handle", "")
        posts = [post for post in self.state["posts"] if handle in post["content"]]
        posts.sort(key=lambda post: post["created_at"], reverse=True)
        return posts

    def _create_post(self, content: str, *, post_type: str, parent_id: str | None = None) -> dict:
        text = str(content).strip()
        if not text:
            raise ValueError("content must not be empty")
        limit = 140 if post_type == "quote" else 500
        if len(text) > limit:
            raise ValueError(f"content exceeds {limit} characters")

        post = {
            "id": f"post_{self.state['next_post_id']}",
            "author": "agent_self",
            "content": text,
            "type": post_type,
            "parent_id": parent_id,
            "likes": [],
            "created_at": f"2026-03-13T10:0{self.state['next_post_id']}Z",
        }
        self.state["next_post_id"] += 1
        self.state["posts"].append(post)
        if parent_id:
            self._add_notification("reply" if post_type == "reply" else "quote", "agent_self", parent_id)
        return dict(post)

    def _like_post(self, post_id: str) -> dict:
        post = self._post_by_id(post_id)
        if "agent_self" not in post["likes"]:
            post["likes"].append("agent_self")
        return dict(post)

    def _follow_agent(self, agent_name: str) -> str:
        if agent_name not in self.state["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")
        if agent_name not in self.state["following"]:
            self.state["following"].append(agent_name)
            self.state["agent"]["following_count"] = len(self.state["following"])
        return agent_name

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        limit = int(arguments.get("limit", 20))
        matches = [
            dict(post)
            for post in self.state["posts"]
            if query in post["content"].lower()
        ]
        matches.sort(key=lambda post: post["created_at"], reverse=True)
        return {"posts": matches[:limit]}

    def _post_by_id(self, post_id: str) -> dict:
        for post in self.state["posts"]:
            if post["id"] == post_id:
                return post
        raise ValueError(f"Unknown post id: {post_id}")

    def _add_notification(self, kind: str, actor: str, post_id: str) -> None:
        self.state["notifications"].append(
            {
                "id": f"notif_{self.state['next_notification_id']}",
                "type": kind,
                "actor": actor,
                "post_id": post_id,
                "read": False,
            }
        )
        self.state["next_notification_id"] += 1

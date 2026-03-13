from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "today": scenario.get("today", "2026-03-13"),
            "threads": [dict(thread) for thread in scenario.get("threads", [])],
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        del conversation_context
        if tool_name == "list":
            return {"threads": [self._summary(thread) for thread in self.state["threads"]]}
        if tool_name == "show":
            thread = self._resolve_thread(arguments["id"])
            return {"thread": dict(thread)}
        if tool_name == "add":
            return self._add(arguments)
        if tool_name == "note":
            return self._append(arguments, field="notes")
        if tool_name == "source":
            return self._append(arguments, field="sources")
        if tool_name == "finding":
            return self._append(arguments, field="findings")
        if tool_name == "status":
            thread = self._resolve_thread(arguments["id"])
            thread["status"] = str(arguments["status"])
            return {"id": thread["id"], "status": thread["status"]}
        if tool_name == "digest":
            active = [self._summary(t) for t in self.state["threads"] if t["status"] == "active"]
            return {"threads": active}
        if tool_name == "decay":
            decayed = []
            for thread in self.state["threads"]:
                if thread["status"] == "active" and not thread["notes"]:
                    thread["status"] = "paused"
                    decayed.append(thread["id"])
            return {"decayed": decayed}
        if tool_name == "covered":
            topics = [thread["title"] for thread in self.state["threads"]]
            urls = [source["url"] for thread in self.state["threads"] for source in thread["sources"]]
            return {"days": int(arguments.get("days", 14)), "topics": topics, "urls": urls}
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {"today": self.state["today"], "threads": [dict(t) for t in self.state["threads"]]}

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _add(self, arguments: dict) -> dict:
        title = str(arguments["title"]).strip()
        slug = title.lower().replace(" ", "-")
        thread = {
            "id": slug,
            "title": title,
            "status": "active",
            "notes": [],
            "sources": [],
            "findings": [],
        }
        self.state["threads"].append(thread)
        return {"id": slug, "title": title}

    def _append(self, arguments: dict, *, field: str) -> dict:
        thread = self._resolve_thread(arguments["id"])
        if field == "sources":
            item = {"url": str(arguments["url"]), "desc": str(arguments.get("desc", ""))}
        else:
            item = {"text": str(arguments["text"]), "date": self.state["today"]}
        thread[field].append(item)
        return {"id": thread["id"], field: list(thread[field])}

    def _resolve_thread(self, prefix: str) -> dict:
        prefix_text = str(prefix)
        matches = [thread for thread in self.state["threads"] if thread["id"].startswith(prefix_text)]
        if len(matches) != 1:
            raise ValueError(f"Expected one thread for {prefix_text}")
        return matches[0]

    def _summary(self, thread: dict) -> dict:
        return {
            "id": thread["id"],
            "title": thread["title"],
            "status": thread["status"],
            "note_count": len(thread["notes"]),
            "source_count": len(thread["sources"]),
            "finding_count": len(thread["findings"]),
        }

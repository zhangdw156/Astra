from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "notes": [self._copy_note(item) for item in scenario.get("notes", [])],
            "sessions": [self._copy_session(item) for item in scenario.get("sessions", [])],
            "config": dict(scenario.get("config", {})),
            "archives": [dict(item) for item in scenario.get("archives", [])],
            "index_ok": bool(scenario.get("index_ok", True)),
            "next_ids": dict(scenario.get("next_ids", {})),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "note":
            return self._note(arguments)
        if tool_name == "session":
            return self._session(arguments, conversation_context)
        if tool_name == "search":
            return self._search(arguments)
        if tool_name == "stats":
            return self._stats()
        if tool_name == "config":
            return self._config(arguments)
        if tool_name == "export":
            return self._export(arguments)
        if tool_name == "import":
            return self._import(arguments)
        if tool_name == "verify":
            return self._verify()
        if tool_name == "repair":
            return self._repair()
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "notes": [self._copy_note(item) for item in self.state["notes"]],
            "sessions": [self._copy_session(item) for item in self.state["sessions"]],
            "config": dict(self.state["config"]),
            "archives": [dict(item) for item in self.state["archives"]],
            "index_ok": self.state["index_ok"],
            "next_ids": dict(self.state["next_ids"]),
        }

    def visible_state(self) -> dict:
        return {
            "notes": [self._present_note(item) for item in self.state["notes"]],
            "sessions": [self._present_session(item) for item in self.state["sessions"]],
            "config": dict(self.state["config"]),
            "archives": [dict(item) for item in self.state["archives"]],
            "index_ok": self.state["index_ok"],
        }

    def _note(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        if action == "add":
            note = {
                "id": self._next_id("note", "note"),
                "category": str(arguments["category"]),
                "title": str(arguments["title"]),
                "content": str(arguments["content"]),
                "tags": self._parse_tags(arguments.get("tags")),
            }
            self.state["notes"].append(note)
            return {"note": self._present_note(note)}
        if action == "search":
            query = str(arguments["query"]).lower()
            category = str(arguments.get("in", "")).strip()
            tag = str(arguments.get("tag", "")).strip()
            notes = []
            for note in self.state["notes"]:
                if category and note["category"] != category:
                    continue
                if tag and tag not in note["tags"]:
                    continue
                text = f"{note['title']} {note['content']}".lower()
                if query in text:
                    notes.append(self._present_note(note, include_excerpt=True))
            return {"notes": notes}
        if action == "list":
            category = str(arguments.get("category", "")).strip()
            notes = self.state["notes"] if not category else [note for note in self.state["notes"] if note["category"] == category]
            return {"notes": [self._present_note(note) for note in notes]}
        if action == "get":
            return {"note": self._present_note(self._note_by_id(str(arguments["id"])), include_content=True)}
        if action == "update":
            note = self._note_by_id(str(arguments["id"]))
            note["title"] = str(arguments.get("title", note["title"]))
            note["content"] = str(arguments.get("content", note["content"]))
            if arguments.get("tags") is not None:
                note["tags"] = self._parse_tags(arguments.get("tags"))
            return {"note": self._present_note(note, include_content=True)}
        if action == "append":
            note = self._note_by_id(str(arguments["id"]))
            addition = str(arguments["content"])
            note["content"] = f"{note['content']}\n{addition}".strip()
            return {"note": self._present_note(note, include_content=True)}
        if action == "delete":
            note_id = str(arguments["id"])
            before = len(self.state["notes"])
            self.state["notes"] = [note for note in self.state["notes"] if note["id"] != note_id]
            return {"deleted": len(self.state["notes"]) < before, "id": note_id}
        if action == "categories":
            return {"categories": sorted({note["category"] for note in self.state["notes"]})}
        if action == "tags":
            tags = sorted({tag for note in self.state["notes"] for tag in note["tags"]})
            return {"tags": tags}
        raise ValueError(f"Unsupported note action: {action}")

    def _session(self, arguments: dict, conversation_context: str | None) -> dict:
        action = str(arguments["action"])
        if action == "save":
            content = str(arguments.get("content", "")).strip()
            if not content:
                content = self._synthesize_session_content(
                    str(arguments.get("title", "Session summary")),
                    conversation_context,
                )
            session = {
                "id": str(arguments.get("session_id", "")) or self._next_id("session", "session"),
                "title": str(arguments["title"]),
                "branch": str(arguments.get("branch", "")),
                "project": str(arguments.get("project", "")),
                "content": content,
                "date": "2026-03-13",
            }
            self.state["sessions"].append(session)
            return {"session": self._present_session(session, include_content=True)}
        if action == "list":
            sessions = list(self.state["sessions"])
            branch = str(arguments.get("branch", "")).strip()
            if branch:
                sessions = [session for session in sessions if session["branch"] == branch]
            last = int(arguments.get("last", len(sessions) or 1))
            sessions = sessions[-last:]
            return {"sessions": [self._present_session(session) for session in sessions]}
        if action == "search":
            query = str(arguments["query"]).lower()
            branch = str(arguments.get("branch", "")).strip()
            sessions = []
            for session in self.state["sessions"]:
                if branch and session["branch"] != branch:
                    continue
                if query in f"{session['title']} {session['content']}".lower():
                    sessions.append(self._present_session(session, include_excerpt=True))
            return {"sessions": sessions}
        if action == "get":
            return {"session": self._present_session(self._session_by_id(str(arguments["id"])), include_content=True)}
        raise ValueError(f"Unsupported session action: {action}")

    def _search(self, arguments: dict) -> dict:
        query = str(arguments["query"]).lower()
        limit = int(arguments.get("limit", 10))
        item_type = str(arguments.get("type", "")).strip()
        results = []
        if item_type in {"", "note"}:
            for note in self.state["notes"]:
                if query in f"{note['title']} {note['content']}".lower():
                    results.append({"type": "note", **self._present_note(note, include_excerpt=True)})
        if item_type in {"", "session"}:
            for session in self.state["sessions"]:
                if query in f"{session['title']} {session['content']}".lower():
                    results.append({"type": "session", **self._present_session(session, include_excerpt=True)})
        return {"results": results[:limit]}

    def _stats(self) -> dict:
        categories = sorted({note["category"] for note in self.state["notes"]})
        tags = sorted({tag for note in self.state["notes"] for tag in note["tags"]})
        return {
            "note_count": len(self.state["notes"]),
            "session_count": len(self.state["sessions"]),
            "categories": categories,
            "tags": tags,
            "archive_count": len(self.state["archives"]),
            "index_ok": self.state["index_ok"],
        }

    def _config(self, arguments: dict) -> dict:
        action = str(arguments["action"])
        if action == "set":
            key = str(arguments["key"])
            self.state["config"][key] = str(arguments["value"])
            return {"key": key, "value": self.state["config"][key]}
        if action == "get":
            key = str(arguments["key"])
            return {"key": key, "value": self.state["config"].get(key)}
        if action == "list":
            return {"config": dict(self.state["config"])}
        if action == "delete":
            key = str(arguments["key"])
            deleted = key in self.state["config"]
            self.state["config"].pop(key, None)
            return {"deleted": deleted, "key": key}
        raise ValueError(f"Unsupported config action: {action}")

    def _export(self, arguments: dict) -> dict:
        filename = str(arguments.get("output_file", "")) or f"claudemem_export_{self._next_id('archive', 'archive')}.tar.gz"
        archive = {
            "archive_file": filename,
            "note_count": len(self.state["notes"]),
            "session_count": len(self.state["sessions"]),
        }
        self.state["archives"].append(archive)
        return dict(archive)

    def _import(self, arguments: dict) -> dict:
        archive_file = str(arguments["archive_file"])
        imported = any(item["archive_file"] == archive_file for item in self.state["archives"])
        if not imported:
            self.state["archives"].append({"archive_file": archive_file, "note_count": 0, "session_count": 0})
        self.state["index_ok"] = True
        return {"imported": True, "archive_file": archive_file}

    def _verify(self) -> dict:
        return {"ok": self.state["index_ok"], "notes_indexed": len(self.state["notes"]), "sessions_indexed": len(self.state["sessions"])}

    def _repair(self) -> dict:
        self.state["index_ok"] = True
        return {"repaired": True, "notes_indexed": len(self.state["notes"]), "sessions_indexed": len(self.state["sessions"])}

    def _note_by_id(self, note_id: str) -> dict:
        for note in self.state["notes"]:
            if note["id"] == note_id:
                return note
        raise ValueError(f"Unknown note id: {note_id}")

    def _session_by_id(self, session_id: str) -> dict:
        for session in self.state["sessions"]:
            if session["id"] == session_id:
                return session
        raise ValueError(f"Unknown session id: {session_id}")

    def _parse_tags(self, raw_tags: object) -> list[str]:
        if raw_tags is None:
            return []
        return [tag.strip() for tag in str(raw_tags).split(",") if tag.strip()]

    def _next_id(self, key: str, prefix: str) -> str:
        current = int(self.state["next_ids"].get(key, 1))
        self.state["next_ids"][key] = current + 1
        return f"{prefix}_{current}"

    def _present_note(
        self,
        note: dict,
        *,
        include_content: bool = False,
        include_excerpt: bool = False,
    ) -> dict:
        payload = {
            "id": note["id"],
            "category": note["category"],
            "title": note["title"],
            "tags": list(note["tags"]),
        }
        if include_content:
            payload["content"] = note["content"]
        if include_excerpt:
            payload["excerpt"] = note["content"][:120]
        return payload

    def _present_session(
        self,
        session: dict,
        *,
        include_content: bool = False,
        include_excerpt: bool = False,
    ) -> dict:
        payload = {
            "id": session["id"],
            "title": session["title"],
            "branch": session["branch"],
            "project": session["project"],
            "date": session["date"],
        }
        if include_content:
            payload["content"] = session["content"]
        if include_excerpt:
            payload["excerpt"] = session["content"][:120]
        return payload

    def _synthesize_session_content(self, title: str, conversation_context: str | None) -> str:
        seed = (conversation_context or "").strip()
        if not seed:
            seed = f"Session: {title}"
        lines = [line.strip() for line in seed.splitlines() if line.strip()]
        summary = " ".join(lines[:4])[:240]
        return f"## Summary\n{summary}\n\n## Next Steps\n- [ ] Continue from saved context"

    def _copy_note(self, note: dict) -> dict:
        return {
            "id": note["id"],
            "category": note["category"],
            "title": note["title"],
            "content": note["content"],
            "tags": list(note.get("tags", [])),
        }

    def _copy_session(self, session: dict) -> dict:
        return {
            "id": session["id"],
            "title": session["title"],
            "branch": session.get("branch", ""),
            "project": session.get("project", ""),
            "content": session["content"],
            "date": session.get("date", ""),
        }

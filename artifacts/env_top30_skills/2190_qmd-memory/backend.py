from __future__ import annotations

from pathlib import Path


class SkillBackend:
    def __init__(self, *, skill_dir: Path, profile: dict):
        self.skill_dir = skill_dir
        self.profile = profile
        self.state: dict = {}

    def load_scenario(self, scenario: dict) -> None:
        self.state = {
            "workspace_root": str(scenario.get("workspace_root", "")),
            "configured": bool(scenario.get("configured", False)),
            "server_running": bool(scenario.get("server_running", False)),
            "index_version": int(scenario.get("index_version", 0)),
            "collections": [self._copy_collection(item) for item in scenario.get("collections", [])],
            "templates_applied": list(scenario.get("templates_applied", [])),
            "last_refresh_summary": scenario.get("last_refresh_summary"),
        }

    def reset(self) -> None:
        self.state = {}

    def call(self, tool_name: str, arguments: dict, conversation_context: str | None = None) -> dict:
        if tool_name == "setup":
            return self._setup()
        if tool_name == "calculate_savings":
            return self._calculate_savings(arguments)
        if tool_name == "refresh":
            return self._refresh()
        if tool_name == "serve":
            return self._serve()
        if tool_name == "add_collection":
            return self._add_collection(arguments)
        if tool_name == "add_context":
            return self._add_context(arguments)
        if tool_name == "apply_template":
            return self._apply_template(arguments)
        if tool_name == "qmd_search":
            return self._search(arguments, mode="keyword")
        if tool_name == "qmd_vsearch":
            return self._search(arguments, mode="semantic")
        if tool_name == "qmd_query":
            return self._query(arguments, conversation_context)
        raise ValueError(f"Unsupported tool: {tool_name}")

    def snapshot_state(self) -> dict:
        return {
            "workspace_root": self.state["workspace_root"],
            "configured": self.state["configured"],
            "server_running": self.state["server_running"],
            "index_version": self.state["index_version"],
            "collections": [self._copy_collection(item) for item in self.state["collections"]],
            "templates_applied": list(self.state["templates_applied"]),
            "last_refresh_summary": self.state["last_refresh_summary"],
        }

    def visible_state(self) -> dict:
        return self.snapshot_state()

    def _setup(self) -> dict:
        self.state["configured"] = True
        self.state["index_version"] = max(self.state["index_version"], 1)
        return {
            "configured": True,
            "collections": [item["name"] for item in self.state["collections"]],
            "workspace_root": self.state["workspace_root"],
        }

    def _calculate_savings(self, arguments: dict) -> dict:
        searches_per_day = int(arguments.get("searches_per_day", 50))
        cost_per_call = float(arguments.get("cost_per_call", 0.03))
        daily_cost = searches_per_day * cost_per_call
        monthly_cost = round(daily_cost * 30, 2)
        annual_cost = round(monthly_cost * 12, 2)
        return {
            "searches_per_day": searches_per_day,
            "cost_per_call": round(cost_per_call, 4),
            "monthly_cost": monthly_cost,
            "annual_cost": annual_cost,
            "monthly_savings": monthly_cost,
            "annual_savings": annual_cost,
        }

    def _refresh(self) -> dict:
        self.state["index_version"] += 1
        summary = {
            "index_version": self.state["index_version"],
            "collection_count": len(self.state["collections"]),
            "document_count": sum(len(item["documents"]) for item in self.state["collections"]),
        }
        self.state["last_refresh_summary"] = summary
        return {"status": "refreshed", **summary}

    def _serve(self) -> dict:
        self.state["server_running"] = True
        return {
            "status": "running",
            "transport": "mcp",
            "workspace_root": self.state["workspace_root"],
            "connection_info": "qmd://local-mcp",
        }

    def _add_collection(self, arguments: dict) -> dict:
        name = str(arguments["name"])
        collection = {
            "name": name,
            "path": str(arguments["path"]),
            "mask": str(arguments.get("mask", "**/*.md")),
            "context": "",
            "documents": [],
        }
        self.state["collections"] = [item for item in self.state["collections"] if item["name"] != name]
        self.state["collections"].append(collection)
        return {"collection": self._present_collection(collection)}

    def _add_context(self, arguments: dict) -> dict:
        target = str(arguments["collection"]).removeprefix("qmd://")
        collection = self._collection_by_name(target)
        collection["context"] = str(arguments["context"])
        return {"collection": self._present_collection(collection)}

    def _apply_template(self, arguments: dict) -> dict:
        template = str(arguments["template"])
        template_defs = {
            "trading": [
                ("intelligence", "intelligence", "**/*.md", "Trading systems, dashboards, signals"),
                ("market-data", "market-data", "**/*.md", "Market data and price history"),
            ],
            "content": [
                ("articles", "articles", "**/*.md", "Published and draft articles"),
                ("ideas", "ideas", "**/*.md", "Content ideas and prompts"),
            ],
            "developer": [
                ("docs", "docs", "**/*.md", "Technical documentation"),
                ("decisions", "decisions", "**/*.md", "Architecture decisions and ADRs"),
            ],
        }
        if template not in template_defs:
            raise ValueError(f"Unsupported template: {template}")
        for name, path, mask, context in template_defs[template]:
            if any(item["name"] == name for item in self.state["collections"]):
                continue
            self.state["collections"].append(
                {"name": name, "path": path, "mask": mask, "context": context, "documents": []}
            )
        if template not in self.state["templates_applied"]:
            self.state["templates_applied"].append(template)
        return {"template": template, "collections": [item["name"] for item in self.state["collections"]]}

    def _search(self, arguments: dict, *, mode: str) -> dict:
        query = str(arguments["query"]).lower()
        limit = int(arguments.get("limit", 10))
        collection_name = str(arguments.get("collection", "")).removeprefix("qmd://").strip()
        matches = []
        for collection in self.state["collections"]:
            if collection_name and collection["name"] != collection_name:
                continue
            for document in collection["documents"]:
                score = self._score_document(query, document["text"], mode)
                if score <= 0:
                    continue
                matches.append(
                    {
                        "collection": collection["name"],
                        "document_id": document["id"],
                        "title": document["title"],
                        "score": round(score, 3),
                        "excerpt": document["text"][:160],
                    }
                )
        matches.sort(key=lambda item: item["score"], reverse=True)
        return {"mode": mode, "results": matches[:limit]}

    def _query(self, arguments: dict, conversation_context: str | None) -> dict:
        base = self._search(arguments, mode="hybrid")["results"]
        query = str(arguments["query"])
        summary = self._synthesize_summary(query, base, conversation_context)
        return {"mode": "hybrid", "results": base, "summary": summary}

    def _score_document(self, query: str, text: str, mode: str) -> float:
        haystack = text.lower()
        tokens = [token for token in query.split() if token]
        if not tokens:
            return 0.0
        raw = sum(token in haystack for token in tokens)
        if raw == 0:
            return 0.0
        if mode == "keyword":
            return float(raw)
        if mode == "semantic":
            return float(raw) + 0.25 * len(tokens)
        return float(raw) + 0.5 * len(tokens)

    def _synthesize_summary(self, query: str, results: list[dict], conversation_context: str | None) -> str:
        if not results:
            return f'No relevant QMD results found for "{query}".'
        top = results[0]
        context_hint = f" Context: {conversation_context[:80]}" if conversation_context else ""
        return f'Most relevant hit is "{top["title"]}" in {top["collection"]}.{context_hint}'.strip()

    def _collection_by_name(self, name: str) -> dict:
        for collection in self.state["collections"]:
            if collection["name"] == name:
                return collection
        raise ValueError(f"Unknown collection: {name}")

    def _present_collection(self, collection: dict) -> dict:
        return {
            "name": collection["name"],
            "path": collection["path"],
            "mask": collection["mask"],
            "context": collection["context"],
            "document_count": len(collection["documents"]),
        }

    def _copy_collection(self, collection: dict) -> dict:
        return {
            "name": collection["name"],
            "path": collection["path"],
            "mask": collection["mask"],
            "context": collection.get("context", ""),
            "documents": [dict(item) for item in collection.get("documents", [])],
        }

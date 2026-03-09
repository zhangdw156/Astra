"""
Trigger Summary Tool - 手动触发摘要

手动触发从短期记忆生成中期摘要的流程。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "trigger_summary",
    "description": "Manually trigger summary generation. Compresses short-term memories into a summary and stores it as medium-term memory. Also clears the short-term memory window after summarization.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
CONFIG_FILE = MEMORY_DIR / "config.json"
SLIDING_WINDOW_FILE = MEMORY_DIR / "sliding-window.json"
SUMMARIES_DIR = MEMORY_DIR / "summaries"

DEFAULT_CONFIG = {
    "memory": {
        "short_term": {"enabled": True, "window_size": 10, "max_tokens": 2000},
        "medium_term": {"enabled": True, "summary_threshold": 4000, "summary_model": "glm-4-flash"},
        "long_term": {"enabled": True, "backend": "chromadb", "top_k": 3, "min_relevance": 0.7},
    }
}


def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    config_json = CONFIG_FILE
    if config_json.exists():
        with open(config_json, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def get_short_term_memory() -> list:
    if not SLIDING_WINDOW_FILE.exists():
        return []
    with open(SLIDING_WINDOW_FILE, "r") as f:
        data = json.load(f)
    return data.get("messages", [])


def add_medium_term_memory(content: str, summary_type: str = "auto"):
    date_str = datetime.now().strftime("%Y-%m-%d")
    summary_file = SUMMARIES_DIR / f"{date_str}.json"

    if summary_file.exists():
        with open(summary_file, "r") as f:
            data = json.load(f)
    else:
        data = {"summaries": [], "date": date_str}

    new_summary = {
        "content": content,
        "type": summary_type,
        "timestamp": datetime.now().isoformat(),
    }
    data["summaries"].append(new_summary)

    with open(summary_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def execute() -> str:
    """触发摘要生成"""
    ensure_dirs()
    config = load_config()

    if not config["memory"]["medium_term"]["enabled"]:
        return "Error: Medium-term memory is not enabled"

    short_memories = get_short_term_memory()

    if not short_memories:
        return "No short-term memories to summarize"

    content_preview = "\n".join([m.get("content", "")[:100] for m in short_memories])
    summary = f"[Auto Summary] {len(short_memories)} messages summarized. Preview: {content_preview[:200]}..."

    add_medium_term_memory(summary, "auto-summary")

    with open(SLIDING_WINDOW_FILE, "w") as f:
        json.dump(
            {"messages": [], "updated_at": datetime.now().isoformat()},
            f,
            indent=2,
            ensure_ascii=False,
        )

    return (
        f"Summary generated and {len(short_memories)} short-term memories archived to medium-term"
    )


if __name__ == "__main__":
    print(execute())

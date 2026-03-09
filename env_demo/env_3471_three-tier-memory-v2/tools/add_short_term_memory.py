"""
Add Short-Term Memory Tool - 添加短期记忆

短期记忆使用滑动窗口机制，保持最近 N 条消息。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "add_short_term_memory",
    "description": "Add a short-term memory using sliding window. Short-term memory keeps the most recent N messages (default 10) in a FIFO queue. Use this for maintaining conversation context during active dialogue.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The content to store in short-term memory",
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata to associate with the memory",
            },
        },
        "required": ["content"],
    },
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
CONFIG_FILE = MEMORY_DIR / "config.json"
SLIDING_WINDOW_FILE = MEMORY_DIR / "sliding-window.json"
SUMMARIES_DIR = MEMORY_DIR / "summaries"
VECTOR_STORE_DIR = MEMORY_DIR / "vector-store"

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
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    config_json = CONFIG_FILE
    if config_json.exists():
        with open(config_json, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def execute(content: str, metadata: dict = None) -> str:
    """添加短期记忆"""
    ensure_dirs()
    config = load_config()
    window_size = config["memory"]["short_term"]["window_size"]

    if not SLIDING_WINDOW_FILE.exists():
        with open(SLIDING_WINDOW_FILE, "w") as f:
            json.dump(
                {"messages": [], "updated_at": datetime.now().isoformat()},
                f,
                indent=2,
                ensure_ascii=False,
            )

    with open(SLIDING_WINDOW_FILE, "r") as f:
        data = json.load(f)

    messages = data.get("messages", [])

    new_message = {
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {},
    }
    messages.append(new_message)

    if len(messages) > window_size:
        messages = messages[-window_size:]

    data["messages"] = messages
    data["updated_at"] = datetime.now().isoformat()

    with open(SLIDING_WINDOW_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return f"Added short-term memory. Current window: {len(messages)}/{window_size}\nLatest: {content[:80]}..."


if __name__ == "__main__":
    print(execute("Test memory content"))

"""
Show Window Tool - 显示短期记忆窗口

显示当前短期记忆窗口中的所有消息。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "show_window",
    "description": "Show the current short-term memory window. Displays all messages currently in the sliding window with timestamps. Use this to see recent conversation context.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
SLIDING_WINDOW_FILE = MEMORY_DIR / "sliding-window.json"


def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def get_short_term_memory() -> list:
    if not SLIDING_WINDOW_FILE.exists():
        return []
    with open(SLIDING_WINDOW_FILE, "r") as f:
        data = json.load(f)
    return data.get("messages", [])


def execute() -> str:
    """显示短期记忆窗口"""
    ensure_dirs()
    messages = get_short_term_memory()

    if not messages:
        return "Short-term memory window is empty"

    output = f"## Short-Term Memory Window ({len(messages)} messages)\n\n"

    for i, msg in enumerate(messages):
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        preview = content[:80] + "..." if len(content) > 80 else content
        output += f"{i + 1}. [{timestamp[:19]}] {preview}\n"

    return output


if __name__ == "__main__":
    print(execute())

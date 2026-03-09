"""
Add Medium-Term Memory Tool - 添加中期记忆

中期记忆通过摘要生成，将短期记忆压缩保存。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "add_medium_term_memory",
    "description": "Add a medium-term memory (summary). Medium-term memory stores summarized versions of conversations when token threshold is exceeded. Use this to archive important conversation summaries.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The summary content to store"},
            "summary_type": {
                "type": "string",
                "default": "manual",
                "description": "Type of summary: 'auto' (auto-generated) or 'manual'",
            },
        },
        "required": ["content"],
    },
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
SUMMARIES_DIR = MEMORY_DIR / "summaries"


def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def execute(content: str, summary_type: str = "manual") -> str:
    """添加中期记忆"""
    ensure_dirs()

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

    return f"Added medium-term memory: {summary_file}\nContent: {content[:80]}..."


if __name__ == "__main__":
    print(execute("Summary of today's conversation about project planning"))

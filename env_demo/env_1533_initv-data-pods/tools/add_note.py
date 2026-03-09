"""
Add Note Tool - Add a note to a data pod

Adds a text note with title, content, and tags to an existing pod.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "add_note",
    "description": "Add a text note to an existing data pod. "
    "Supports title, content, and tags for organization. "
    "Notes are stored in local SQLite database.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pod_name": {"type": "string", "description": "Name of the pod to add the note to"},
            "title": {"type": "string", "description": "Title of the note"},
            "content": {"type": "string", "description": "Content/body of the note"},
            "tags": {
                "type": "string",
                "default": "",
                "description": "Comma-separated tags for organization (e.g., 'ai, research, notes')",
            },
        },
        "required": ["pod_name", "title", "content"],
    },
}


def execute(pod_name: str, title: str, content: str, tags: str = "") -> str:
    """Add a note to a pod."""
    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found.\n\nCreate it first with: create_pod"

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO notes (title, content, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (title, content, tags, now, now),
    )

    note_id = c.lastrowid
    conn.commit()
    conn.close()

    return f"✅ Added note to '{pod_name}'\n📝 Title: {title}\n🏷️ Tags: {tags}\n🆔 Note ID: {note_id}\n⏰ Created: {now}"


if __name__ == "__main__":
    print(execute("test-pod", "Test Note", "This is a test note content", "test, demo"))

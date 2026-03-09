"""
Query Pod Tool - Search notes in a data pod

Performs text search or SQL queries against a pod's notes.
"""

import sqlite3
from pathlib import Path

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "query_pod",
    "description": "Search notes in a data pod. "
    "Supports text search (keywords) and raw SQL queries. "
    "Text search looks for matches in title and content.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pod_name": {"type": "string", "description": "Name of the pod to query"},
            "text": {
                "type": "string",
                "description": "Text to search for in notes (title and content)",
            },
            "sql": {"type": "string", "description": "Raw SQL query (advanced users only)"},
        },
        "required": ["pod_name"],
    },
}


def execute(pod_name: str, text: str = None, sql: str = None) -> str:
    """Query a pod for notes."""
    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found"

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if sql:
        try:
            c.execute(sql)
            rows = c.fetchall()
            if rows:
                output = f"📊 SQL Query Results ({len(rows)} rows):\n\n"
                for row in rows:
                    output += f"{row}\n"
            else:
                output = "No results found."
        except Exception as e:
            output = f"SQL Error: {e}"
    elif text:
        c.execute(
            "SELECT id, title, content, tags FROM notes WHERE content LIKE ? OR title LIKE ?",
            (f"%{text}%", f"%{text}%"),
        )
        rows = c.fetchall()
        if rows:
            output = f"🔍 Found {len(rows)} results for '{text}':\n\n"
            for row in rows:
                content_preview = row[2][:100] + "..." if len(row[2]) > 100 else row[2]
                output += f"**[{row[0]}] {row[1]}**\n"
                output += f"   {content_preview}\n"
                if row[3]:
                    output += f"   🏷️ {row[3]}\n"
                output += "\n"
        else:
            output = f"No results found for '{text}'"
    else:
        c.execute("SELECT id, title, tags, created_at FROM notes ORDER BY created_at DESC")
        rows = c.fetchall()
        if rows:
            output = f"📄 Notes in '{pod_name}' ({len(rows)} total):\n\n"
            for row in rows:
                output += f"**[{row[0]}] {row[1]}**\n"
                output += f"   🏷️ {row[2] or 'no tags'} | {row[3]}\n\n"
        else:
            output = "No notes yet. Add one with: add_note"

    conn.close()
    return output


if __name__ == "__main__":
    print(execute("test-pod", "test"))

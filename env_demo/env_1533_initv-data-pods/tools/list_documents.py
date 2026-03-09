"""
List Documents Tool - List all documents in a data pod

Shows all ingested documents in a pod with metadata.
"""

import sqlite3
from pathlib import Path

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "list_documents",
    "description": "List all documents ingested into a data pod. "
    "Shows filename, type, hash, and creation date.",
    "inputSchema": {
        "type": "object",
        "properties": {"pod_name": {"type": "string", "description": "Name of the pod"}},
        "required": ["pod_name"],
    },
}


def execute(pod_name: str) -> str:
    """List documents in a pod."""
    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found"

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        "SELECT id, filename, file_type, file_hash, created_at FROM documents ORDER BY created_at DESC"
    )
    rows = c.fetchall()

    conn.close()

    if not rows:
        return f"No documents in '{pod_name}'.\n\nRun ingest_folder to add documents."

    output = f"📄 Documents in '{pod_name}' ({len(rows)} total):\n\n"
    for row in rows:
        output += f"**[{row[0]}] {row[1]}** ({row[2]})\n"
        output += f"   Hash: {row[3]} | Added: {row[4][:10]}\n\n"

    return output


if __name__ == "__main__":
    print(execute("test-pod"))

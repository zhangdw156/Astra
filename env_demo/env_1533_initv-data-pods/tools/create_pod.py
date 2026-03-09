"""
Create Pod Tool - Create a new data pod

Creates a new modular portable database pod with SQLite storage.
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import yaml

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "create_pod",
    "description": "Create a new modular portable database pod. "
    "Pods store notes, documents, and embeddings locally in SQLite. "
    "Types: scholar (research), health (biometrics), projects (workspace), shared (group).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name for the new pod (no spaces, use underscores)",
            },
            "pod_type": {
                "type": "string",
                "default": "shared",
                "enum": ["scholar", "health", "shared", "projects"],
                "description": "Type of pod: scholar, health, shared, or projects",
            },
        },
        "required": ["name"],
    },
}


def execute(name: str, pod_type: str = "shared") -> str:
    """Create a new data pod."""
    PODS_DIR.mkdir(parents=True, exist_ok=True)
    pod_path = PODS_DIR / name

    if pod_path.exists():
        return f"Error: Pod '{name}' already exists at {pod_path}"

    pod_path.mkdir(parents=True, exist_ok=True)

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        tags TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER,
        chunk_text TEXT,
        embedding BLOB,
        FOREIGN KEY(note_id) REFERENCES notes(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_type TEXT,
        content TEXT,
        file_hash TEXT,
        chunks TEXT,
        embedding BLOB,
        created_at TEXT,
        updated_at TEXT
    )""")

    conn.commit()
    conn.close()

    metadata = {
        "name": name,
        "type": pod_type,
        "created": datetime.now().isoformat(),
        "version": "0.1",
        "tables": ["notes", "embeddings", "documents"],
    }
    (pod_path / "metadata.json").write_text(json.dumps(metadata, indent=2))

    manifest = {
        "name": name,
        "type": pod_type,
        "access": "private",
        "created": metadata["created"],
        "version": "0.1",
    }
    (pod_path / "manifest.yaml").write_text(yaml.dump(manifest))

    return f"✅ Created pod: {name} (type: {pod_type})\n📁 Location: {pod_path}\n\nTables created: notes, embeddings, documents"


if __name__ == "__main__":
    print(execute("test-pod", "scholar"))

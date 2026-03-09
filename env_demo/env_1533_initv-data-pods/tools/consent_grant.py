"""
Consent Grant Tool - Grant agent access to pods

Creates a consent session allowing an agent to access specified pods.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import uuid

CONSENT_DIR = Path.home() / ".openclaw" / "consent"

TOOL_SCHEMA = {
    "name": "consent_grant",
    "description": "Grant an agent access to specified pods. "
    "Creates a consent session with optional expiration. "
    "Agents must have valid consent to access pod data.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pods": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of pod names to grant access to",
            },
            "agent": {
                "type": "string",
                "default": "cli",
                "description": "Agent name to grant access to",
            },
            "duration_minutes": {
                "type": "integer",
                "default": 60,
                "description": "Session duration in minutes",
            },
        },
        "required": ["pods"],
    },
}


def execute(pods: list, agent: str = "cli", duration_minutes: int = 60) -> str:
    """Grant consent to pods for an agent."""
    CONSENT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CONSENT_DIR / "consent.db"

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        agent TEXT,
        pods_allowed TEXT,
        created_at TEXT,
        expires_at TEXT
    )""")
    conn.commit()

    session_id = str(uuid.uuid4())
    created = datetime.now()
    expires = created + timedelta(minutes=duration_minutes)

    c.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        (session_id, agent, ",".join(pods), created.isoformat(), expires.isoformat()),
    )
    conn.commit()
    conn.close()

    return (
        f"✅ Granted access to {len(pods)} pods\n"
        f"🤖 Agent: {agent}\n"
        f"📋 Session ID: {session_id}\n"
        f"📦 Pods: {', '.join(pods)}\n"
        f"⏰ Expires: {expires.strftime('%Y-%m-%d %H:%M')}"
    )


if __name__ == "__main__":
    print(execute(["test-pod"], "openclaw", 60))

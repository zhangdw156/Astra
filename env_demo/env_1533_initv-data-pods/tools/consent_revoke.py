"""
Consent Revoke Tool - Revoke agent access to pods

Revokes a previously granted consent session.
"""

import sqlite3
from pathlib import Path

CONSENT_DIR = Path.home() / ".openclaw" / "consent"

TOOL_SCHEMA = {
    "name": "consent_revoke",
    "description": "Revoke an agent's access to pods by session ID. "
    "Immediately terminates the consent session.",
    "inputSchema": {
        "type": "object",
        "properties": {"session_id": {"type": "string", "description": "Session ID to revoke"}},
        "required": ["session_id"],
    },
}


def execute(session_id: str) -> str:
    """Revoke consent for a session."""
    CONSENT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CONSENT_DIR / "consent.db"

    if not db_path.exists():
        return "No consent sessions found."

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

    return f"✅ Revoked session: {session_id}"


if __name__ == "__main__":
    print(execute("test-session-id"))

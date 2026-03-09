"""
Consent Status Tool - Show consent status

Displays active consent sessions and their status.
"""

import sqlite3
from pathlib import Path

CONSENT_DIR = Path.home() / ".openclaw" / "consent"

TOOL_SCHEMA = {
    "name": "consent_status",
    "description": "Show consent status for all sessions or a specific session. "
    "Displays active sessions, agent names, allowed pods, and expiration times.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Specific session ID to check (optional)",
            }
        },
    },
}


def execute(session_id: str = None) -> str:
    """Show consent status."""
    CONSENT_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CONSENT_DIR / "consent.db"

    if not db_path.exists():
        return "No consent sessions found."

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    if session_id:
        c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = c.fetchone()
        conn.close()

        if row:
            return (
                f"📋 Session Details\n\n"
                f"ID: {row[0]}\n"
                f"Agent: {row[1]}\n"
                f"Pods: {row[2]}\n"
                f"Created: {row[3]}\n"
                f"Expires: {row[4]}"
            )
        else:
            return f"No session found: {session_id}"
    else:
        c.execute("SELECT id, agent, pods_allowed, expires_at FROM sessions")
        rows = c.fetchall()
        conn.close()

        if not rows:
            return "No active sessions."

        output = "📋 Active Consent Sessions\n\n"
        for row in rows:
            output += f"**[{row[0][:8]}...]** {row[1]}\n"
            output += f"   Pods: {row[2]}\n"
            output += f"   Expires: {row[3]}\n\n"

        return output


if __name__ == "__main__":
    print(execute())

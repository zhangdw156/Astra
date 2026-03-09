"""
Schedule Draft Tool - Schedule or publish a Typefully draft

Schedules a draft for future publication or publishes immediately.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "schedule_draft",
    "description": "Schedule a Typefully draft for publication or publish immediately. "
    "Use 'now' to publish immediately, 'next-free-slot' for queue scheduling, "
    "or provide an ISO 8601 timestamp.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The ID of the draft to schedule"},
            "schedule_time": {
                "type": "string",
                "description": "Schedule time: ISO 8601 (e.g., 2026-03-01T09:00:00Z), 'next-free-slot', or 'now' for immediate publish",
            },
        },
        "required": ["draft_id", "schedule_time"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str, schedule_time: str) -> str:
    """
    Schedule a draft

    Args:
        draft_id: The draft ID
        schedule_time: Schedule time (ISO 8601, 'next-free-slot', or 'now')

    Returns:
        JSON response
    """
    body = json.dumps({"publish_at": schedule_time}).encode()
    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}"

    request = urllib.request.Request(url, data=body, method="PUT")
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output = "## Draft Scheduled\n\n"
        output += f"**Draft ID: {draft_id}**\n"
        output += f"- Scheduled for: {schedule_time}\n"
        output += f"- Status: {result.get('status', 'scheduled')}\n"

        return output
    except Exception as e:
        return f"Error scheduling draft: {str(e)}"


if __name__ == "__main__":
    print(execute("123456", "next-free-slot"))

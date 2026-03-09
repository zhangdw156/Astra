"""
Schedule Draft Tool - 计划或发布 Typefully 草稿

设置草稿的发布时间。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "schedule_draft",
    "description": "Schedule or publish a Typefully draft. "
    "Use ISO 8601 format for specific time, 'next-free-slot' for queue scheduling, "
    "or 'now' to publish immediately (use with caution).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The draft ID to schedule"},
            "schedule": {
                "type": "string",
                "description": "Schedule time: ISO 8601 ('2026-03-01T09:00:00Z'), 'next-free-slot', or 'now'",
            },
        },
        "required": ["draft_id", "schedule"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str, schedule: str) -> str:
    """
    计划草稿

    Args:
        draft_id: 草稿 ID
        schedule: 发布时间

    Returns:
        计划结果
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts/{draft_id}"

        body = {"publish_at": schedule}
        json_data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Authorization": f"Bearer {TYPEFULLY_API_KEY}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Draft Scheduled Successfully\n\n"
        output += f"**Draft ID:** {draft_id}\n"
        output += f"**Publish At:** {schedule}\n"
        output += f"**Status:** {data.get('status', 'scheduled')}\n"

        return output

    except Exception as e:
        return f"Error scheduling draft: {str(e)}"


if __name__ == "__main__":
    print(execute("8196074", "next-free-slot"))

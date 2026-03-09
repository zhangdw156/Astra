"""
List Drafts Tool - List Typefully drafts

Lists drafts with optional status filter.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_drafts",
    "description": "List Typefully drafts. Can filter by status (draft, scheduled, published). "
    "Use this to see existing drafts before creating or editing.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: draft, scheduled, or published (leave empty for all)",
                "default": "",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of drafts to return",
                "default": 10,
            },
        },
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(status: str = "", limit: int = 10) -> str:
    """
    List Typefully drafts

    Args:
        status: Filter by status (draft, scheduled, published, or empty for all)
        limit: Maximum number of drafts

    Returns:
        JSON string of drafts
    """
    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts?limit={limit}"
    if status:
        url += f"&status={status}"

    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Typefully Drafts\n\n"
        if isinstance(data, list) and data:
            for draft in data:
                output += f"**ID: {draft.get('id')}**\n"
                output += f"- Status: {draft.get('status', 'unknown')}\n"
                output += f"- Created: {draft.get('created_at', 'N/A')}\n"
                if draft.get("publish_at"):
                    output += f"- Scheduled: {draft.get('publish_at')}\n"
                output += "\n"
        elif isinstance(data, dict) and data.get("drafts"):
            for draft in data["drafts"]:
                output += f"**ID: {draft.get('id')}**\n"
                output += f"- Status: {draft.get('status', 'unknown')}\n"
                output += f"- Created: {draft.get('created_at', 'N/A')}\n"
                if draft.get("publish_at"):
                    output += f"- Scheduled: {draft.get('publish_at')}\n"
                output += "\n"
        else:
            output += "No drafts found\n"

        return output
    except Exception as e:
        return f"Error listing drafts: {str(e)}"


if __name__ == "__main__":
    print(execute())

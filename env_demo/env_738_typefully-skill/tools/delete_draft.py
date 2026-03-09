"""
Delete Draft Tool - Delete a Typefully draft

Deletes a draft by ID.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "delete_draft",
    "description": "Delete a Typefully draft by its ID. This action cannot be undone.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The ID of the draft to delete"}
        },
        "required": ["draft_id"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str) -> str:
    """
    Delete a draft

    Args:
        draft_id: The draft ID

    Returns:
        Confirmation message
    """
    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}"

    request = urllib.request.Request(url, method="DELETE")
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = response.read().decode()

        output = "## Draft Deleted\n\n"
        output += f"**Draft ID: {draft_id}** has been deleted.\n"

        return output
    except Exception as e:
        return f"Error deleting draft: {str(e)}"


if __name__ == "__main__":
    print(execute("123456"))

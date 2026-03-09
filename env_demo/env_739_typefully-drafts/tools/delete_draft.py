"""
Delete Draft Tool - 删除 Typefully 草稿

删除指定的草稿。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "delete_draft",
    "description": "Delete a Typefully draft by ID. "
    "Use this to remove unwanted drafts. Cannot be undone.",
    "inputSchema": {
        "type": "object",
        "properties": {"draft_id": {"type": "string", "description": "The draft ID to delete"}},
        "required": ["draft_id"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str) -> str:
    """
    删除草稿

    Args:
        draft_id: 草稿 ID

    Returns:
        删除结果
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts/{draft_id}"

        request = urllib.request.Request(
            url, method="DELETE", headers={"Authorization": f"Bearer {TYPEFULLY_API_KEY}"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            _ = response.read()

        output = "## Draft Deleted Successfully\n\n"
        output += f"**Draft ID:** {draft_id}\n"
        output += "The draft has been permanently deleted.\n"

        return output

    except Exception as e:
        return f"Error deleting draft: {str(e)}"


if __name__ == "__main__":
    print(execute("8196074"))

"""
Get Draft Tool - Get details of a specific Typefully draft

Retrieves full details of a draft by ID.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_draft",
    "description": "Get full details of a specific Typefully draft by its ID. "
    "Use this to view the complete content before editing.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The ID of the draft to retrieve"}
        },
        "required": ["draft_id"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str) -> str:
    """
    Get a specific draft

    Args:
        draft_id: The draft ID

    Returns:
        Draft details
    """
    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}"

    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Draft Details\n\n"
        output += f"**ID: {data.get('id', draft_id)}**\n"
        output += f"- Status: {data.get('status', 'unknown')}\n"
        output += f"- Created: {data.get('created_at', 'N/A')}\n"
        output += f"- Updated: {data.get('updated_at', 'N/A')}\n"
        if data.get("publish_at"):
            output += f"- Scheduled: {data.get('publish_at')}\n"

        if data.get("content") or data.get("posts"):
            output += "\n### Content\n"
            content = data.get("content") or data.get("posts", [])
            if isinstance(content, list):
                for i, post in enumerate(content):
                    if isinstance(post, dict):
                        output += f"**Post {i + 1}:** {post.get('text', '')}\n\n"
                    else:
                        output += f"**Post {i + 1}:** {post}\n\n"
            else:
                output += f"{content}\n"

        return output
    except Exception as e:
        return f"Error getting draft: {str(e)}"


if __name__ == "__main__":
    print(execute("123456"))

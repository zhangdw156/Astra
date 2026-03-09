"""
Edit Draft Tool - Edit an existing Typefully draft

Updates the content of an existing draft.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "edit_draft",
    "description": "Edit an existing Typefully draft. Supports updating text and changing platform settings. "
    "Use get_draft first to see current content.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The ID of the draft to edit"},
            "text": {
                "type": "string",
                "description": "New text content. For threads, separate posts with '---'",
            },
            "is_thread": {
                "type": "boolean",
                "description": "Whether this is a thread (multiple posts separated by ---)",
                "default": False,
            },
            "platforms": {
                "type": "string",
                "description": "Comma-separated platforms: x, linkedin, threads, bluesky, mastodon (default: x)",
                "default": "x",
            },
        },
        "required": ["draft_id", "text"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str, text: str, is_thread: bool = False, platforms: str = "x") -> str:
    """
    Edit an existing draft

    Args:
        draft_id: The draft ID
        text: New text content
        is_thread: Whether it's a thread
        platforms: Comma-separated platforms

    Returns:
        JSON response
    """
    if is_thread:
        posts = [{"text": p.strip()} for p in text.split("---")]
    else:
        posts = [{"text": text}]

    platforms_json = {}
    for p in platforms.split(","):
        p = p.strip()
        if p:
            platforms_json[p] = {"enabled": True, "posts": posts}

    body = {"platforms": platforms_json}
    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}"
    data = json.dumps(body).encode()

    request = urllib.request.Request(url, data=data, method="PUT")
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output = "## Draft Updated\n\n"
        output += f"**Draft ID: {draft_id}**\n"
        output += f"Status: {result.get('status', 'updated')}\n"

        return output
    except Exception as e:
        return f"Error editing draft: {str(e)}"


if __name__ == "__main__":
    print(execute("123456", "Updated text"))

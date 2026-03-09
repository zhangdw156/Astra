"""
Create Draft Tool - Create a new Typefully draft

Creates a new draft with optional thread support and multi-platform posting.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "create_draft",
    "description": "Create a new Typefully draft. Supports single tweets, threads (separated by ---), "
    "and multi-platform posting (x, linkedin, threads, bluesky, mastodon). "
    "Can also schedule the draft for a specific time.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text content of the draft. For threads, separate posts with '---'",
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
            "schedule": {
                "type": "string",
                "description": "Schedule time: ISO 8601 (e.g., 2026-03-01T09:00:00Z), 'next-free-slot', or empty for draft",
                "default": "",
            },
        },
        "required": ["text"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(text: str, is_thread: bool = False, platforms: str = "x", schedule: str = "") -> str:
    """
    Create a new Typefully draft

    Args:
        text: Draft text content
        is_thread: Whether it's a thread
        platforms: Comma-separated platforms
        schedule: Schedule time or empty

    Returns:
        JSON response with draft ID
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
    if schedule:
        body["publish_at"] = schedule

    url = f"{TYPEFULLY_API_BASE}/social-sets/{TYPEFULLY_SOCIAL_SET_ID}/drafts"
    data = json.dumps(body).encode()

    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output = "## Draft Created\n\n"
        if isinstance(result, dict):
            output += f"**Draft ID: {result.get('id', result.get('draft_id', 'unknown'))}**\n"
            output += f"- Status: {result.get('status', 'draft')}\n"
            if result.get("publish_at"):
                output += f"- Scheduled: {result.get('publish_at')}\n"
        else:
            output += f"```json\n{json.dumps(result, indent=2)}\n```\n"

        return output
    except Exception as e:
        return f"Error creating draft: {str(e)}"


if __name__ == "__main__":
    print(execute("Test tweet"))

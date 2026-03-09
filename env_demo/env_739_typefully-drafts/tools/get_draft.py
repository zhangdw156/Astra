"""
Get Draft Tool - 获取单个 Typefully 草稿详情

获取指定草稿的完整信息。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_draft",
    "description": "Get full details of a specific Typefully draft by ID. "
    "Use this to retrieve the complete content of a draft including all posts and metadata.",
    "inputSchema": {
        "type": "object",
        "properties": {"draft_id": {"type": "string", "description": "The draft ID to retrieve"}},
        "required": ["draft_id"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str) -> str:
    """
    获取草稿详情

    Args:
        draft_id: 草稿 ID

    Returns:
        格式化的草稿详情
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts/{draft_id}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = f"## Draft Details: {draft_id}\n\n"
        output += f"**Status:** {data.get('status', 'unknown')}\n"

        if data.get("publish_at"):
            output += f"**Scheduled:** {data.get('publish_at')}\n"

        if data.get("created_at"):
            output += f"**Created:** {data.get('created_at')}\n"

        output += "\n### Content\n\n"

        platforms = data.get("platforms", {})
        for platform, info in platforms.items():
            output += f"**{platform.upper()}**\n"
            posts = info.get("posts", [])
            for i, post in enumerate(posts):
                output += f"Post {i + 1}: {post.get('text', '')}\n\n"

        return output

    except Exception as e:
        return f"Error getting draft: {str(e)}"


if __name__ == "__main__":
    print(execute("8196074"))

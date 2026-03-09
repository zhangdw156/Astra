"""
List Drafts Tool - 列出 Typefully 草稿

列出用户的草稿，支持按状态过滤。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_drafts",
    "description": "List Typefully drafts. Supports filtering by status (draft, scheduled, published). "
    "Use this to see existing drafts before creating new ones or to check draft status.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filter by status: 'draft', 'scheduled', 'published'. Omit for all drafts.",
                "enum": ["draft", "scheduled", "published", ""],
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of drafts to return",
            },
        },
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(status: str = "", limit: int = 10) -> str:
    """
    列出草稿

    Args:
        status: 过滤状态 (draft, scheduled, published)
        limit: 返回数量限制

    Returns:
        格式化的草稿列表
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts?limit={limit}"
        if status:
            url += f"&status={status}"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Typefully Drafts\n\n"

        drafts = data if isinstance(data, list) else data.get("drafts", [])
        if not drafts:
            output += "No drafts found.\n"
            return output

        for draft in drafts:
            output += f"**Draft ID: {draft.get('id')}**\n"
            output += f"- Status: {draft.get('status', 'unknown')}\n"
            output += f"- Platform: {list(draft.get('platforms', {}).keys())}\n"
            if draft.get("publish_at"):
                output += f"- Scheduled: {draft.get('publish_at')}\n"
            posts = draft.get("platforms", {}).get("x", {}).get("posts", [])
            if posts:
                text = posts[0].get("text", "")[:100]
                output += f"- Preview: {text}...\n"
            output += "\n"

        output += f"Total: {len(drafts)} drafts\n"
        return output

    except Exception as e:
        return f"Error listing drafts: {str(e)}"


if __name__ == "__main__":
    print(execute())

"""
Edit Draft Tool - 编辑 Typefully 草稿

编辑现有草稿的内容。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "edit_draft",
    "description": "Edit an existing Typefully draft. Update the content of a draft. "
    "Supports editing single tweets or threads (use --thread flag).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "draft_id": {"type": "string", "description": "The draft ID to edit"},
            "text": {
                "type": "string",
                "description": "New content for the draft. For threads, separate posts with '\\n---\\n'",
            },
            "is_thread": {
                "type": "boolean",
                "default": False,
                "description": "Whether the text is a thread",
            },
            "platforms": {
                "type": "string",
                "default": "x",
                "description": "Platforms to update: x, linkedin",
            },
        },
        "required": ["draft_id", "text"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(draft_id: str, text: str, is_thread: bool = False, platforms: str = "x") -> str:
    """
    编辑草稿

    Args:
        draft_id: 草稿 ID
        text: 新内容
        is_thread: 是否为线程
        platforms: 平台

    Returns:
        编辑结果
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts/{draft_id}"

        posts = []
        if is_thread:
            parts = text.replace("\\n---\\n", "\n---\n").split("\n---\n")
            for part in parts:
                posts.append({"text": part.strip()})
        else:
            posts.append({"text": text})

        platform_dict = {}
        for p in platforms.split(","):
            platform_dict[p.strip()] = {"enabled": True, "posts": posts}

        body = {"platforms": platform_dict}
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

        output = "## Draft Updated Successfully\n\n"
        output += f"**Draft ID:** {draft_id}\n"
        output += f"**Status:** {data.get('status', 'updated')}\n"

        return output

    except Exception as e:
        return f"Error editing draft: {str(e)}"


if __name__ == "__main__":
    print(execute("8196074", "Updated content"))

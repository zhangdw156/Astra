"""
Create Draft Tool - 创建 Typefully 草稿

创建新的草稿，支持单条推文、线程和多平台发布。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "create_draft",
    "description": "Create a new Typefully draft. Supports single tweets, threads (use --thread flag), "
    "and multi-platform posts (X, LinkedIn, Threads, Bluesky, Mastodon). "
    "For threads, separate posts with '\\n---\\n' in the text.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The content of the draft. For threads, separate posts with '\\n---\\n'",
            },
            "is_thread": {
                "type": "boolean",
                "default": False,
                "description": "Whether to treat the text as a thread (multiple posts)",
            },
            "platforms": {
                "type": "string",
                "default": "x",
                "description": "Comma-separated platforms: x, linkedin, threads, bluesky, mastodon",
            },
            "schedule": {
                "type": "string",
                "description": "Schedule time: ISO 8601 (e.g., '2026-03-01T09:00:00Z'), 'next-free-slot', or leave empty for draft",
                "default": "",
            },
        },
        "required": ["text"],
    },
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")
SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "123456")


def execute(text: str, is_thread: bool = False, platforms: str = "x", schedule: str = "") -> str:
    """
    创建草稿

    Args:
        text: 草稿内容
        is_thread: 是否为线程
        platforms: 平台列表
        schedule: 计划发布时间

    Returns:
        创建结果
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets/{SOCIAL_SET_ID}/drafts"

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
        if schedule:
            body["publish_at"] = schedule

        json_data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=json_data,
            headers={
                "Authorization": f"Bearer {TYPEFULLY_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Draft Created Successfully\n\n"
        output += f"**Draft ID:** {data.get('id', 'N/A')}\n"
        output += f"**Status:** {data.get('status', 'draft')}\n"
        if schedule:
            output += f"**Scheduled:** {schedule}\n"
        output += f"**Platforms:** {platforms}\n"
        output += f"**Thread:** {'Yes' if is_thread else 'No'}\n"

        return output

    except Exception as e:
        return f"Error creating draft: {str(e)}"


if __name__ == "__main__":
    print(execute("Just shipped a new feature!"))

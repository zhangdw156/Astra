"""
Post to Both Tool - 同时发布到 Twitter 和 Farcaster

一次发布同时到两个平台。
"""

import os
import json
import urllib.request

TOOL_SCHEMA = {
    "name": "post_to_both",
    "description": "Post to both Twitter and Farcaster simultaneously. Use this to cross-post to both platforms at once. Each platform has its own character/byte limits.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Post text content (will be truncated if exceeding either platform's limit)",
            },
            "image_path": {"type": "string", "description": "Optional path to image to attach"},
            "account": {
                "type": "string",
                "description": "Optional Twitter account name for multi-account support",
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "Preview without posting",
            },
        },
        "required": ["text"],
    },
}

TWITTER_API_BASE = os.environ.get("TWITTER_API_BASE", "http://localhost:8003")
FARCASTER_API_BASE = os.environ.get("FARCASTER_API_BASE", "http://localhost:8004")


def execute(text: str, image_path: str = None, account: str = None, dry_run: bool = False) -> str:
    """
    同时发布到 Twitter 和 Farcaster

    Args:
        text: 发布内容
        image_path: 可选图片路径
        account: 可选 Twitter 账户
        dry_run: 仅预览不发布

    Returns:
        发布结果
    """
    output = "## Post to Both Platforms\n\n"

    if dry_run:
        output += "### Draft Preview\n\n"
        output += f"**Text:**\n{text}\n\n"
        output += "**Targets:**\n"
        output += "  - Twitter\n"
        output += "  - Farcaster\n\n"
        if image_path:
            output += f"**Image:** {image_path}\n\n"
        output += "This is a dry run - no posts were made."
        return output

    output += "### Twitter\n"
    try:
        url = f"{TWITTER_API_BASE}/tweets"
        payload = {"text": text, "account": account}
        if image_path:
            payload["image_path"] = image_path

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output += f"**Success!** Tweet ID: {result.get('tweet_id', 'N/A')}\n\n"

    except Exception as e:
        output += f"**Failed:** {str(e)}\n\n"

    output += "### Farcaster\n"
    try:
        url = f"{FARCASTER_API_BASE}/casts"
        payload = {"text": text}
        if image_path:
            payload["image_path"] = image_path

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output += f"**Success!** Cast Hash: {result.get('hash', 'N/A')}\n"
        output += f"**Cost:** ~0.001 USDC\n"

    except Exception as e:
        output += f"**Failed:** {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("Test post to both"))

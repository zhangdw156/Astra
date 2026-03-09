"""
Post to Twitter Tool - 发布推文到 Twitter

使用 Twitter API 发布推文，支持文字和图片。
"""

import os
import json
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "post_to_twitter",
    "description": "Post a tweet to Twitter. Supports text and images. Twitter has a 280 character limit (252 with 10% safety buffer). Use this for Twitter-only posts.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Tweet text content (max 252 characters with safety buffer)",
            },
            "image_path": {"type": "string", "description": "Optional path to image to attach"},
            "account": {
                "type": "string",
                "description": "Optional account name for multi-account support (lowercase prefix from .env)",
            },
            "vary": {
                "type": "boolean",
                "default": False,
                "description": "Auto-vary text to avoid duplicate content detection",
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
TWITTER_API_KEY = os.environ.get("X_CONSUMER_KEY", "mock-consumer-key")
TWITTER_API_SECRET = os.environ.get("X_CONSUMER_SECRET", "mock-consumer-secret")
TWITTER_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "mock-access-token")
TWITTER_ACCESS_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET", "mock-access-secret")


def execute(
    text: str,
    image_path: str = None,
    account: str = None,
    vary: bool = False,
    dry_run: bool = False,
) -> str:
    """
    发布推文到 Twitter

    Args:
        text: 推文内容
        image_path: 可选图片路径
        account: 可选账户名称
        vary: 自动调整文本避免重复检测
        dry_run: 仅预览不发布

    Returns:
        发布结果
    """
    output = "## Post to Twitter\n\n"

    if dry_run:
        output += "### Draft Preview\n\n"
        output += f"**Text:**\n{text}\n\n"
        if image_path:
            output += f"**Image:** {image_path}\n\n"
        if account:
            output += f"**Account:** {account}\n\n"
        output += "This is a dry run - no post was made."
        return output

    try:
        url = f"{TWITTER_API_BASE}/tweets"

        payload = {"text": text, "account": account, "vary": vary}
        if image_path:
            payload["image_path"] = image_path

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output += "### Success\n\n"
        output += f"**Tweet ID:** {result.get('tweet_id', 'N/A')}\n"
        output += f"**URL:** {result.get('url', 'N/A')}\n"
        output += f"**Text:** {result.get('text', text)}\n"

    except Exception as e:
        output += f"### Error\n\n"
        output += f"Failed to post tweet: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("Test tweet from MCP"))

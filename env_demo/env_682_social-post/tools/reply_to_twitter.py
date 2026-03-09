"""
Reply to Twitter Tool - 回复推文

回复特定推文。
"""

import os
import json
import urllib.request

TOOL_SCHEMA = {
    "name": "reply_to_twitter",
    "description": "Reply to an existing tweet. Use the tweet ID from the original tweet URL (twitter.com/user/status/TWEET_ID).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "tweet_id": {
                "type": "string",
                "description": "Tweet ID to reply to (from twitter.com/user/status/TWEET_ID)",
            },
            "text": {"type": "string", "description": "Reply text content (max 252 characters)"},
            "image_path": {"type": "string", "description": "Optional path to image to attach"},
            "account": {
                "type": "string",
                "description": "Optional account name for multi-account support",
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "Preview without posting",
            },
        },
        "required": ["tweet_id", "text"],
    },
}

TWITTER_API_BASE = os.environ.get("TWITTER_API_BASE", "http://localhost:8003")


def execute(
    tweet_id: str, text: str, image_path: str = None, account: str = None, dry_run: bool = False
) -> str:
    """
    回复推文

    Args:
        tweet_id: 要回复的推文 ID
        text: 回复内容
        image_path: 可选图片路径
        account: 可选账户
        dry_run: 仅预览不发布

    Returns:
        回复结果
    """
    output = "## Reply to Twitter\n\n"
    output += f"**Replying to Tweet ID:** {tweet_id}\n\n"

    if dry_run:
        output += "### Draft Preview\n\n"
        output += f"**Text:**\n{text}\n\n"
        if image_path:
            output += f"**Image:** {image_path}\n\n"
        output += "This is a dry run - no reply was posted."
        return output

    try:
        url = f"{TWITTER_API_BASE}/tweets/reply"

        payload = {"tweet_id": tweet_id, "text": text, "account": account}
        if image_path:
            payload["image_path"] = image_path

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output += "### Success\n\n"
        output += f"**Reply Tweet ID:** {result.get('tweet_id', 'N/A')}\n"
        output += f"**URL:** {result.get('url', 'N/A')}\n"
        output += f"**Text:** {result.get('text', text)}\n"

    except Exception as e:
        output += f"### Error\n\n"
        output += f"Failed to reply: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("1234567890123456789", "Great point!"))

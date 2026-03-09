"""
Reply to Farcaster Tool - 回复 Cast

回复特定的 Cast。
"""

import os
import json
import urllib.request

TOOL_SCHEMA = {
    "name": "reply_to_farcaster",
    "description": "Reply to an existing cast. Use the cast hash from the original cast URL (farcaster.xyz/~/conversations/HASH). Each reply costs 0.001 USDC.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "cast_hash": {
                "type": "string",
                "description": "Cast hash to reply to (from farcaster.xyz/~/conversations/HASH)",
            },
            "text": {"type": "string", "description": "Reply text content (max 288 bytes)"},
            "image_path": {"type": "string", "description": "Optional path to image to attach"},
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "Preview without posting",
            },
        },
        "required": ["cast_hash", "text"],
    },
}

FARCASTER_API_BASE = os.environ.get("FARCASTER_API_BASE", "http://localhost:8004")
FARCASTER_API_KEY = os.environ.get("FARCASTER_API_KEY", "mock-api-key")


def execute(cast_hash: str, text: str, image_path: str = None, dry_run: bool = False) -> str:
    """
    回复 Cast

    Args:
        cast_hash: 要回复的 Cast hash
        text: 回复内容
        image_path: 可选图片路径
        dry_run: 仅预览不发布

    Returns:
        回复结果
    """
    output = "## Reply to Farcaster\n\n"
    output += f"**Replying to Cast:** {cast_hash}\n\n"

    if dry_run:
        output += "### Draft Preview\n\n"
        output += f"**Text:**\n{text}\n\n"
        if image_path:
            output += f"**Image:** {image_path}\n\n"
        output += "This is a dry run - no reply was posted."
        return output

    try:
        url = f"{FARCASTER_API_BASE}/casts/reply"

        payload = {"cast_hash": cast_hash, "text": text}
        if image_path:
            payload["image_path"] = image_path

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {FARCASTER_API_KEY}",
            },
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())

        output += "### Success\n\n"
        output += f"**Reply Cast Hash:** {result.get('hash', 'N/A')}\n"
        output += f"**URL:** {result.get('url', 'N/A')}\n"
        output += f"**Text:** {result.get('text', text)}\n"
        output += f"**Cost:** ~0.001 USDC\n"

    except Exception as e:
        output += f"### Error\n\n"
        output += f"Failed to reply: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("0xa1b2c3d4e5f6", "Great insight!"))

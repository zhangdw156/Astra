"""
Post to Farcaster Tool - 发布 Cast 到 Farcaster

使用 Neynar API 发布 Cast，支持文字和图片。
"""

import os
import json
import urllib.request

TOOL_SCHEMA = {
    "name": "post_to_farcaster",
    "description": "Post a cast to Farcaster. Supports text and images. Farcaster has a 288 byte limit (320 with 10% safety buffer). Each cast costs 0.001 USDC.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Cast text content (max 288 bytes)"},
            "image_path": {
                "type": "string",
                "description": "Optional path to image to attach (will be uploaded to imgur)",
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

FARCASTER_API_BASE = os.environ.get("FARCASTER_API_BASE", "http://localhost:8004")
FARCASTER_API_KEY = os.environ.get("FARCASTER_API_KEY", "mock-api-key")


def execute(text: str, image_path: str = None, dry_run: bool = False) -> str:
    """
    发布 Cast 到 Farcaster

    Args:
        text: Cast 内容
        image_path: 可选图片路径
        dry_run: 仅预览不发布

    Returns:
        发布结果
    """
    output = "## Post to Farcaster\n\n"

    if dry_run:
        output += "### Draft Preview\n\n"
        output += f"**Text:**\n{text}\n\n"
        if image_path:
            output += f"**Image:** {image_path}\n\n"
        output += "This is a dry run - no cast was made."
        return output

    try:
        url = f"{FARCASTER_API_BASE}/casts"

        payload = {"text": text}
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
        output += f"**Cast Hash:** {result.get('hash', 'N/A')}\n"
        output += f"**URL:** {result.get('url', 'N/A')}\n"
        output += f"**Text:** {result.get('text', text)}\n"
        output += f"**Cost:** ~0.001 USDC\n"

    except Exception as e:
        output += f"### Error\n\n"
        output += f"Failed to post cast: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("Test cast from MCP"))

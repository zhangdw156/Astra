"""
Preview Post Tool - 预览发布内容

在发布前预览内容，检查字符限制等。
"""

TOOL_SCHEMA = {
    "name": "preview_post",
    "description": "Preview a post before publishing. Shows character/byte count, validates limits, and displays exactly what will be posted. Use this to check if content fits within platform limits.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Post text content to preview"},
            "platform": {
                "type": "string",
                "enum": ["twitter", "farcaster", "both"],
                "default": "both",
                "description": "Platform to validate against (twitter: 252 chars, farcaster: 288 bytes)",
            },
            "image_path": {"type": "string", "description": "Optional path to image"},
        },
        "required": ["text"],
    },
}


def execute(text: str, platform: str = "both", image_path: str = None) -> str:
    """
    预览发布内容

    Args:
        text: 要预览的内容
        platform: 验证平台
        image_path: 可选图片路径

    Returns:
        预览结果
    """
    output = "## Post Preview\n\n"

    char_count = len(text)
    byte_count = len(text.encode("utf-8"))

    output += "### Content\n\n"
    output += "```\n"
    output += text
    output += "\n```\n\n"

    output += "### Character/Byte Count\n\n"
    output += f"- Characters: {char_count}\n"
    output += f"- Bytes: {byte_count}\n\n"

    twitter_limit = 252
    farcaster_limit = 288

    output += "### Validation\n\n"

    if platform in ("twitter", "both"):
        twitter_ok = char_count <= twitter_limit
        output += f"**Twitter:** {char_count}/{twitter_limit} characters "
        if twitter_ok:
            output += "✓ OK\n"
        else:
            output += f"✗ EXCEEDS LIMIT ({char_count - twitter_limit} over)\n"

    if platform in ("farcaster", "both"):
        farcaster_ok = byte_count <= farcaster_limit
        output += f"**Farcaster:** {byte_count}/{farcaster_limit} bytes "
        if farcaster_ok:
            output += "✓ OK\n"
        else:
            output += f"✗ EXCEEDS LIMIT ({byte_count - farcaster_limit} over)\n"

    if image_path:
        output += f"\n**Image:** {image_path}\n"

    output += "\n### Tips\n"
    output += "- Use `--truncate` flag to auto-truncate if over limit\n"
    output += "- Use `--thread` flag for long text to split into numbered posts\n"
    output += "- Use `--shorten-links` to save characters on URLs\n"

    return output


if __name__ == "__main__":
    print(execute("gm! Building onchain 🦞"))

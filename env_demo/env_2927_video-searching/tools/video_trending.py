"""
Video Trending Tool - Get trending videos across platforms

Get trending/popular videos from YouTube, TikTok, Instagram, and Twitter/X.
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "video_trending",
    "description": "Get trending or popular videos from YouTube, TikTok, Instagram, and Twitter/X. "
    "Use this to discover what's currently trending across social video platforms.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["all", "music", "tech", "gaming", "news", "entertainment", "sports"],
                "default": "all",
                "description": "Category to filter trending videos",
            },
            "region": {
                "type": "string",
                "default": "us",
                "description": "Region code (us, eu, asia, etc.)",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of videos to return",
            },
        },
    },
}

VIDEO_API_BASE = os.environ.get("VIDEO_API_BASE", "http://localhost:8001")


def execute(category: str = "all", region: str = "us", limit: int = 10) -> str:
    """
    Get trending videos

    Args:
        category: Category filter
        region: Region code
        limit: Maximum results

    Returns:
        Formatted trending videos
    """
    output = f"## Trending Videos: {category} ({region.upper()})\n\n"

    try:
        url = f"{VIDEO_API_BASE}/videos/trending?category={category}&region={region}&limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("videos"):
            for idx, video in enumerate(data["videos"], 1):
                output += f"### {idx}. {video.get('title', 'Untitled')}\n"
                output += f"- **Platform**: {video.get('platform', 'unknown')}\n"
                output += f"- **URL**: {video.get('url', 'N/A')}\n"
                output += f"- **Views**: {video.get('views', 'N/A')}\n"
                output += f"- **Likes**: {video.get('likes', 'N/A')}\n"
                output += f"- **Trend Score**: {video.get('trend_score', 'N/A')}\n\n"
        else:
            output += "No trending videos found.\n"

    except Exception as e:
        output += f"Error fetching trending videos: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("tech"))

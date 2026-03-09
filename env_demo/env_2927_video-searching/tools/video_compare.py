"""
Video Compare Tool - Compare videos across platforms

Compare and analyze videos across multiple platforms (YouTube, TikTok, Instagram, Twitter/X).
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "video_compare",
    "description": "Compare and analyze videos across YouTube, TikTok, Instagram, and Twitter/X. "
    "Use this to get a cross-platform analysis of videos on a specific topic, "
    "comparing metrics, engagement, and content patterns.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Topic to compare videos across platforms"},
            "platforms": {
                "type": "array",
                "items": {"type": "string", "enum": ["youtube", "tiktok", "instagram", "twitter"]},
                "default": ["youtube", "tiktok", "twitter"],
                "description": "Platforms to include in comparison",
            },
            "limit_per_platform": {
                "type": "integer",
                "default": 3,
                "description": "Number of videos per platform to compare",
            },
        },
        "required": ["query"],
    },
}

VIDEO_API_BASE = os.environ.get("VIDEO_API_BASE", "http://localhost:8001")


def execute(query: str, platforms: list = None, limit_per_platform: int = 3) -> str:
    """
    Compare videos across platforms

    Args:
        query: Topic to compare
        platforms: List of platforms to include
        limit_per_platform: Videos per platform

    Returns:
        Formatted comparison results
    """
    if platforms is None:
        platforms = ["youtube", "tiktok", "twitter"]

    output = f"## Video Comparison: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        platforms_str = ",".join(platforms)
        url = f"{VIDEO_API_BASE}/videos/compare?q={encoded_query}&platforms={platforms_str}&limit={limit_per_platform}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("platforms"):
            for platform_data in data["platforms"]:
                platform = platform_data.get("platform", "unknown")
                output += f"### {platform.upper()}\n\n"

                videos = platform_data.get("videos", [])
                if videos:
                    for video in videos:
                        output += f"**{video.get('title', 'Untitled')}**\n"
                        output += f"- URL: {video.get('url', 'N/A')}\n"
                        output += f"- Views: {video.get('views', 'N/A')}\n"
                        output += f"- Engagement: {video.get('engagement', 'N/A')}\n\n"
                else:
                    output += "No videos found\n\n"

        summary = data.get("summary", "")
        if summary:
            output += f"**Analysis Summary:**\n{summary}\n"

    except Exception as e:
        output += f"Error comparing videos: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("AI technology"))

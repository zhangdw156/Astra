"""
Video Search Tool - Search for videos across platforms

Search for social videos (YouTube, TikTok, Instagram, Twitter/X) based on query.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "video_search",
    "description": "Search for social videos across YouTube, TikTok, Instagram, and Twitter/X. "
    "Use this to find videos matching a specific topic, keyword, or trend.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g., 'AI news', 'tesla review', 'cooking tutorial')",
            },
            "platform": {
                "type": "string",
                "enum": ["youtube", "tiktok", "instagram", "twitter", "all"],
                "default": "all",
                "description": "Platform to search: youtube, tiktok, instagram, twitter, or all",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of videos to return",
            },
        },
        "required": ["query"],
    },
}

VIDEO_API_BASE = os.environ.get("VIDEO_API_BASE", "http://localhost:8001")


def execute(query: str, platform: str = "all", limit: int = 10) -> str:
    """
    Search for videos across platforms

    Args:
        query: Search query
        platform: Platform to search (youtube, tiktok, instagram, twitter, all)
        limit: Maximum results

    Returns:
        Formatted search results
    """
    output = f"## Video Search Results: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{VIDEO_API_BASE}/videos/search?q={encoded_query}&platform={platform}&limit={limit}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if data.get("videos"):
            for idx, video in enumerate(data["videos"], 1):
                output += f"### {idx}. {video.get('title', 'Untitled')}\n"
                output += f"- **Platform**: {video.get('platform', 'unknown')}\n"
                output += f"- **URL**: {video.get('url', 'N/A')}\n"
                output += f"- **Duration**: {video.get('duration', 'N/A')}\n"
                output += f"- **Views**: {video.get('views', 'N/A')}\n"
                output += f"- **Relevance**: {video.get('relevance_note', 'N/A')}\n\n"
        else:
            output += "No videos found for the given query.\n"

    except Exception as e:
        output += f"Error searching videos: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("AI news"))

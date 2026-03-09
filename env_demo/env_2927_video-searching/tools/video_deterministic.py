"""
Video Sourcing Deterministic Tool - Deterministic /video_sourcing command

Run the Video Sourcing Agent with deterministic, concise chat UX.
This tool is triggered when user uses /video_sourcing command.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "video_deterministic",
    "description": "Run deterministic video sourcing via /video_sourcing command. "
    "Use this when user explicitly invokes /video_sourcing with a query. "
    "Returns structured results with top 3 video references.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Video search query after /video_sourcing command",
            },
            "event_detail": {
                "type": "string",
                "enum": ["compact", "verbose"],
                "default": "compact",
                "description": "Output detail level: compact (short) or verbose (full)",
            },
        },
        "required": ["query"],
    },
}

VIDEO_API_BASE = os.environ.get("VIDEO_API_BASE", "http://localhost:8001")


def execute(query: str, event_detail: str = "compact") -> str:
    """
    Run deterministic video sourcing

    Args:
        query: Search query
        event_detail: compact or verbose output

    Returns:
        Formatted video sourcing results
    """
    output = f"## Video Sourcing: {query}\n\n"

    try:
        encoded_query = urllib.parse.quote(query)
        url = f"{VIDEO_API_BASE}/videos/sourcing?query={encoded_query}&event_detail={event_detail}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        event_type = data.get("event", "unknown")

        if event_type == "started":
            output += "Starting video sourcing...\n\n"

        if event_type == "complete":
            videos = data.get("videos", [])
            output += data.get("summary", "Search complete.\n\n")

            if videos:
                output += "### Top Video References\n\n"
                for idx, video in enumerate(videos[:3], 1):
                    output += f"**{idx}. {video.get('title', 'Untitled')}**\n"
                    output += f"- URL: {video.get('url', 'N/A')}\n"
                    output += f"- Relevance: {video.get('relevance_note', 'N/A')}\n\n"

            tools_used = data.get("tools_used", [])
            if tools_used:
                output += f"Tools used: {', '.join(tools_used)}\n"

        elif event_type == "clarification_needed":
            output += (
                f"Clarification needed: {data.get('question', 'Please provide more details.')}\n"
            )

        elif event_type == "error":
            output += f"Error: {data.get('error', 'Unknown error')}\n"
            output += f"Next step: {data.get('next_step', 'Try again with a different query.')}\n"

    except Exception as e:
        output += f"Error running video sourcing: {str(e)}\n"

    return output


if __name__ == "__main__":
    print(execute("bitcoin price prediction"))

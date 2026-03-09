"""
List Social Sets Tool - List available Typefully social sets

Lists available social sets (accounts) for the user.
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_social_sets",
    "description": "List available Typefully social sets (accounts). "
    "Use this to find your social set ID if you have multiple accounts.",
    "inputSchema": {"type": "object", "properties": {}},
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8001")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")


def execute() -> str:
    """
    List social sets

    Returns:
        JSON string of social sets
    """
    url = f"{TYPEFULLY_API_BASE}/social-sets"

    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")
    request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Typefully Social Sets\n\n"
        if isinstance(data, list) and data:
            for ss in data:
                output += f"**ID: {ss.get('id')}**\n"
                output += f"- Name: {ss.get('name', 'N/A')}\n"
                output += f"- Platform: {ss.get('platform', 'N/A')}\n"
                output += "\n"
        else:
            output += "No social sets found\n"

        return output
    except Exception as e:
        return f"Error listing social sets: {str(e)}"


if __name__ == "__main__":
    print(execute())

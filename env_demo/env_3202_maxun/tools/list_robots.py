"""
List Robots Tool - 列出所有 Maxun 机器人
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_robots",
    "description": "List all Maxun web scraping robots. Use this to see what robots are available. Maxun is a web scraping platform where users create robots to scrape websites.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of robots to return",
            }
        },
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(limit: int = 10) -> str:
    """
    列出所有机器人

    Args:
        limit: 返回的最大数量

    Returns:
        格式化的机器人列表
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots?limit={limit}"

        request = urllib.request.Request(url)
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        robots = data.get("data", [])

        if not robots:
            return "No robots found. Create one at https://app.maxun.dev"

        output = f"Found {len(robots)} robot(s):\n\n"

        for r in robots:
            meta = r.get("recording_meta", {})
            output += f"**ID:** {meta.get('id', r.get('id', ''))}\n"
            output += f"**Name:** {meta.get('name', '')}\n"
            output += f"**Type:** {meta.get('type', '')}\n"
            output += f"**URL:** {meta.get('url', '')}\n"
            output += "\n"

        return output

    except Exception as e:
        return f"Error listing robots: {str(e)}"


if __name__ == "__main__":
    print(execute())

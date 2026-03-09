"""
Get Robot Tool - 获取机器人详情
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_robot",
    "description": "Get details of a specific Maxun robot by ID. Use this to see robot configuration, target URL, and other details.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "robot_id": {"type": "string", "description": "The robot ID to get details for"}
        },
        "required": ["robot_id"],
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(robot_id: str) -> str:
    """
    获取机器人详情

    Args:
        robot_id: 机器人 ID

    Returns:
        格式化的机器人详情
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots/{robot_id}"

        request = urllib.request.Request(url)
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        robot = data.get("data", data)

        output = f"## Robot Details: {robot_id}\n\n"
        output += f"**ID:** {robot.get('id', robot_id)}\n"

        meta = robot.get("recording_meta", {})
        output += f"**Name:** {meta.get('name', 'N/A')}\n"
        output += f"**Type:** {meta.get('type', 'N/A')}\n"
        output += f"**URL:** {meta.get('url', 'N/A')}\n"

        if robot.get("config"):
            output += f"\n**Config:**\n"
            output += f"```json\n{json.dumps(robot.get('config'), indent=2)}\n```\n"

        return output

    except Exception as e:
        return f"Error getting robot: {str(e)}"


if __name__ == "__main__":
    print(execute("robot-123"))

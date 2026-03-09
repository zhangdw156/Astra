"""
List Runs Tool - 列出机器人的所有运行记录
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_runs",
    "description": "List all runs for a specific Maxun robot. Use this to see the execution history of a robot.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "robot_id": {"type": "string", "description": "The robot ID to list runs for"}
        },
        "required": ["robot_id"],
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(robot_id: str) -> str:
    """
    列出所有运行记录

    Args:
        robot_id: 机器人 ID

    Returns:
        格式化的运行列表
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots/{robot_id}/runs"

        request = urllib.request.Request(url)
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        runs = data.get("data", [])

        if not runs:
            return f"No runs found for robot {robot_id}"

        output = f"## Runs for Robot: {robot_id}\n\n"
        output += f"Total runs: {len(runs)}\n\n"

        for r in runs:
            output += f"**Run ID:** {r.get('runId', '')}  |  "
            output += f"**Status:** {r.get('status', '?')}  |  "
            output += f"**Started:** {r.get('startedAt', '')}\n"

        return output

    except Exception as e:
        return f"Error listing runs: {str(e)}"


if __name__ == "__main__":
    print(execute("robot-123"))

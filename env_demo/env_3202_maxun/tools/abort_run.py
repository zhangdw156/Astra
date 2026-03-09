"""
Abort Run Tool - 中止正在运行的机器人
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "abort_run",
    "description": "Abort a running Maxun robot execution. Use this to stop a robot that is currently scraping.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "robot_id": {"type": "string", "description": "The robot ID"},
            "run_id": {"type": "string", "description": "The run ID to abort"},
        },
        "required": ["robot_id", "run_id"],
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(robot_id: str, run_id: str) -> str:
    """
    中止运行

    Args:
        robot_id: 机器人 ID
        run_id: 运行 ID

    Returns:
        中止结果
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots/{robot_id}/runs/{run_id}/abort"

        request = urllib.request.Request(url, method="POST")
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = f"## Abort Request\n\n"
        output += f"**Robot ID:** {robot_id}\n"
        output += f"**Run ID:** {run_id}\n\n"
        output += f"```json\n{json.dumps(data, indent=2)}\n```\n"

        return output

    except Exception as e:
        return f"Error aborting run: {str(e)}"


if __name__ == "__main__":
    print(execute("robot-123", "run-456"))

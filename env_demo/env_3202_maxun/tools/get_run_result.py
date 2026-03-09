"""
Get Run Result Tool - 获取运行结果
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "get_run_result",
    "description": "Get the result of a specific robot run. Use this to retrieve the scraped data from a previous execution.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "robot_id": {"type": "string", "description": "The robot ID"},
            "run_id": {"type": "string", "description": "The run ID to get results for"},
        },
        "required": ["robot_id", "run_id"],
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(robot_id: str, run_id: str) -> str:
    """
    获取运行结果

    Args:
        robot_id: 机器人 ID
        run_id: 运行 ID

    Returns:
        格式化的运行结果
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots/{robot_id}/runs/{run_id}"

        request = urllib.request.Request(url)
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        run = data.get("data", data)

        output = f"## Run Result\n\n"
        output += f"**Run ID:** {run.get('runId', run.get('id', 'N/A'))}\n"
        output += f"**Status:** {run.get('status', 'N/A')}\n"
        output += f"**Started:** {run.get('startedAt', 'N/A')}\n"
        output += f"**Finished:** {run.get('finishedAt', 'N/A')}\n\n"

        output_data = run.get("serializableOutput", {})

        if output_data:
            output += "### Output Data\n"

            text_data = output_data.get("textData", {})
            list_data = output_data.get("listData", [])
            crawl_data = output_data.get("crawlData", [])
            search_data = output_data.get("searchData", {})

            if text_data:
                output += f"```json\n{json.dumps(text_data, indent=2)}\n```\n"

            if list_data:
                output += f"List Data ({len(list_data)} items):\n"
                output += f"```json\n{json.dumps(list_data[:5], indent=2)}\n```\n"

            if crawl_data:
                output += f"Crawl Data ({len(crawl_data)} pages):\n"
                output += f"```json\n{json.dumps(crawl_data[:3], indent=2)}\n```\n"

            if search_data:
                output += f"```json\n{json.dumps(search_data, indent=2)}\n```\n"
        else:
            output += "No output yet. The run may still be in progress.\n"

        return output

    except Exception as e:
        return f"Error getting run result: {str(e)}"


if __name__ == "__main__":
    print(execute("robot-123", "run-456"))

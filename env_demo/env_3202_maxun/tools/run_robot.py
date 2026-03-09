"""
Run Robot Tool - 执行机器人爬取
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "run_robot",
    "description": "Execute a Maxun robot to scrape a website. This runs the robot synchronously and waits for the result. Use this to scrape data from a target website.",
    "inputSchema": {
        "type": "object",
        "properties": {"robot_id": {"type": "string", "description": "The robot ID to execute"}},
        "required": ["robot_id"],
    },
}

MAXUN_API_BASE = os.environ.get("MAXUN_API_BASE", "http://localhost:8001")
MAXUN_API_KEY = os.environ.get("MAXUN_API_KEY", "mock-api-key")


def execute(robot_id: str) -> str:
    """
    执行机器人

    Args:
        robot_id: 机器人 ID

    Returns:
        执行结果
    """
    try:
        url = f"{MAXUN_API_BASE}/api/sdk/robots/{robot_id}/execute"

        request = urllib.request.Request(url, method="POST")
        request.add_header("x-api-key", MAXUN_API_KEY)
        request.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode())

        result = data.get("data", data)

        output = f"## Robot Execution: {robot_id}\n\n"
        output += f"**Run ID:** {result.get('runId', 'N/A')}\n"
        output += f"**Status:** {result.get('status', 'N/A')}\n\n"

        extracted = result.get("data", {})
        text_data = extracted.get("textData", {})
        list_data = extracted.get("listData", [])
        crawl_data = extracted.get("crawlData", [])
        search_data = extracted.get("searchData", {})

        if text_data:
            output += "### Text Data\n"
            output += f"```json\n{json.dumps(text_data, indent=2)}\n```\n"

        if list_data:
            output += f"### List Data ({len(list_data)} items)\n"
            output += f"```json\n{json.dumps(list_data[:5], indent=2)}\n```\n"
            if len(list_data) > 5:
                output += f"... and {len(list_data) - 5} more items\n"

        if crawl_data:
            output += f"### Crawl Data ({len(crawl_data)} pages)\n"
            output += f"```json\n{json.dumps(crawl_data[:3], indent=2)}\n```\n"

        if search_data:
            output += "### Search Data\n"
            output += f"```json\n{json.dumps(search_data, indent=2)}\n```\n"

        if not any([text_data, list_data, crawl_data, search_data]):
            output += "No data extracted yet.\n"

        return output

    except Exception as e:
        return f"Error running robot: {str(e)}"


if __name__ == "__main__":
    print(execute("robot-123"))

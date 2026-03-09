"""
List Social Sets Tool - 列出 Typefully 社交账号集

列出用户所有可用的社交账号集。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "list_social_sets",
    "description": "List all available social sets (accounts) in Typefully. "
    "Use this to find your social set ID if you have multiple accounts connected.",
    "inputSchema": {"type": "object", "properties": {}},
}

TYPEFULLY_API_BASE = os.environ.get("TYPEFULLY_API_BASE", "http://localhost:8003")
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "mock-api-key")


def execute() -> str:
    """
    列出社交账号集

    Returns:
        格式化的社交账号集列表
    """
    try:
        url = f"{TYPEFULLY_API_BASE}/social-sets"

        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bearer {TYPEFULLY_API_KEY}")

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode())

        output = "## Typefully Social Sets\n\n"

        social_sets = data if isinstance(data, list) else data.get("social_sets", [])
        if not social_sets:
            output += "No social sets found. Connect an account in Typefully first.\n"
            return output

        for ss in social_sets:
            output += f"**ID: {ss.get('id')}**\n"
            output += f"- Handle: @{ss.get('handle', 'N/A')}\n"
            output += f"- Platform: {ss.get('platform', 'N/A')}\n"
            output += f"- Account: {ss.get('account_name', 'N/A')}\n"
            output += "\n"

        output += f"Total: {len(social_sets)} social set(s)\n"
        output += (
            "\nSet `TYPEFULLY_SOCIAL_SET_ID` environment variable to use a specific account.\n"
        )

        return output

    except Exception as e:
        return f"Error listing social sets: {str(e)}"


if __name__ == "__main__":
    print(execute())

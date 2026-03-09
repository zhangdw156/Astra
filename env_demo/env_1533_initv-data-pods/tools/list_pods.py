"""
List Pods Tool - List all available data pods

Shows all pods stored in ~/.openclaw/data-pods/
"""

import json
from pathlib import Path

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "list_pods",
    "description": "List all available data pods. "
    "Shows pod name, type, and creation date. "
    "Use this to see what pods exist before adding content or querying.",
    "inputSchema": {"type": "object", "properties": {}},
}


def execute() -> str:
    """List all available pods."""
    PODS_DIR.mkdir(parents=True, exist_ok=True)

    pods = []
    for d in PODS_DIR.iterdir():
        if d.is_dir():
            meta = d / "metadata.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text())
                    pods.append(
                        {
                            "name": d.name,
                            "type": data.get("type", "unknown"),
                            "created": data.get("created", "unknown"),
                            "version": data.get("version", "unknown"),
                        }
                    )
                except:
                    pods.append(
                        {
                            "name": d.name,
                            "type": "unknown",
                            "created": "unknown",
                            "version": "unknown",
                        }
                    )
            else:
                pods.append(
                    {"name": d.name, "type": "unknown", "created": "unknown", "version": "unknown"}
                )

    if not pods:
        return "📦 No pods found.\n\nCreate one with: create_pod"

    output = f"📦 Available pods ({len(pods)}):\n\n"
    for p in pods:
        output += f"- **{p['name']}** ({p['type']})\n"
        output += f"  Created: {p['created'][:10] if p['created'] != 'unknown' else 'unknown'} | Version: {p['version']}\n\n"

    return output


if __name__ == "__main__":
    print(execute())

"""
Export Pod Tool - Export a pod as a ZIP file

Exports a pod as a portable ZIP file that can be shared or backed up.
"""

import zipfile
from pathlib import Path
import hashlib

PODS_DIR = Path.home() / ".openclaw" / "data-pods"
SYNC_DIR = Path.home() / ".openclaw" / "sync"

TOOL_SCHEMA = {
    "name": "export_pod",
    "description": "Export a data pod as a ZIP file for sharing or backup. "
    "Creates a portable .vpod file containing SQLite database, metadata, and manifest.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pod_name": {"type": "string", "description": "Name of the pod to export"},
            "output_path": {
                "type": "string",
                "description": "Output file path (default: ~/.openclaw/sync/<pod_name>.vpod)",
            },
        },
        "required": ["pod_name"],
    },
}


def execute(pod_name: str, output_path: str = None) -> str:
    """Export a pod as ZIP."""
    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found"

    if output_path is None:
        SYNC_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(SYNC_DIR / f"{pod_name}.vpod")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in pod_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(pod_path)
                zipf.write(file, arcname)

    with open(output_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()[:16]

    size_kb = output_path.stat().st_size / 1024

    return f"✅ Exported '{pod_name}'\n📁 File: {output_path}\n🔒 Hash: {file_hash}\n📊 Size: {size_kb:.1f} KB"


if __name__ == "__main__":
    print(execute("test-pod"))

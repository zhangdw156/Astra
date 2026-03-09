"""
Extract Data Images Tool - Extract data:image from HTML

Extract base64-encoded images from HTML content.
"""

import json
import os
import re
import subprocess

TOOL_SCHEMA = {
    "name": "extract_data_images",
    "description": "Extract data:image (base64) images from HTML content. "
    "Many login pages embed QR codes as base64 in the HTML. "
    "This tool extracts these images and saves them to files.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "html_path": {
                "type": "string",
                "description": "Path to HTML JSON file (from browser-use get html)",
            },
            "output_dir": {"type": "string", "description": "Directory to save extracted images"},
        },
        "required": ["html_path", "output_dir"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(html_path: str, output_dir: str) -> str:
    """
    Extract data:image from HTML

    Args:
        html_path: Path to HTML JSON file
        output_dir: Directory for output images

    Returns:
        Extraction result
    """
    os.makedirs(output_dir, exist_ok=True)

    script = f"""
import base64
import json
import os
import re
from pathlib import Path

html_path = "{html_path}"
output_dir = "{output_dir}"

# Load HTML data
with open(html_path, 'r') as f:
    data = json.load(f)

html_content = data.get('data', {{}}).get('html', '')

# Find all data:image patterns
pattern = r'data:image/([^;]+);base64,([A-Za-z0-9+/=]+)'
matches = re.findall(pattern, html_content)

print(f"Found {{len(matches)}} data:image files")

for i, (img_type, base64_data) in enumerate(matches):
    try:
        img_bytes = base64.b64decode(base64_data)
        ext = 'png' if img_type == 'png' else img_type if img_type else 'jpg'
        filename = f"image_{{i}}.{{ext}}"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        
        print(f"Saved: {{filepath}} ({{len(img_bytes)}} bytes)")
    except Exception as e:
        print(f"Error decoding image {{i}}: {{e}}")

print(f"Extracted {{len(matches)}} images to {{output_dir}}")
"""

    try:
        result = subprocess.run(
            ["python3", "-c", script], capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            return f"""## Extract Data Images

**HTML File**: {html_path}
**Output**: {output_dir}

**Status**: Success

```
{result.stdout}
```
"""
        else:
            return f"""## Extract Data Images

**HTML File**: {html_path}
**Output**: {output_dir}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""
    except FileNotFoundError:
        return f"""## Extract Data Images

**Status**: Error

Python3 not found.
"""
    except Exception as e:
        return f"""## Extract Data Images

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("/tmp/page_html.json", "/tmp/data_imgs"))

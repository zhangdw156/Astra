"""
Crop Candidates Tool - Generate QR code crop candidates from screenshot

Generate multiple likely QR code crop regions from a screenshot.
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "crop_candidates",
    "description": "Generate multiple likely QR code crop regions from a screenshot. "
    "Use this to extract potential QR codes from login/demo pages. "
    "The tool generates several crop candidates that can be scanned.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input_path": {"type": "string", "description": "Path to input screenshot"},
            "output_dir": {"type": "string", "description": "Directory to save cropped images"},
        },
        "required": ["input_path", "output_dir"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(input_path: str, output_dir: str) -> str:
    """
    Crop QR candidates from screenshot

    Args:
        input_path: Path to input screenshot
        output_dir: Directory for output crops

    Returns:
        Crop generation result
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # This would run a Python script to crop candidates
    # For now, return a message about how to use it
    script = f"""
import cv2
import numpy as np
import os
from pathlib import Path

input_path = "{input_path}"
output_dir = "{output_dir}"

img = cv2.imread(input_path)
if img is None:
    print(f"Error: Could not read image from {{input_path}}")
    exit(1)

h, w = img.shape[:2]

# Generate multiple crop candidates for potential QR codes
# These are heuristic regions based on common login page layouts

crops = [
    # Center crops
    ("center_300x300", h//2 - 150, w//2 - 150, 300, 300),
    ("center_250x250", h//2 - 125, w//2 - 125, 250, 250),
    # Corner regions
    ("top_right_200x200", 10, w-210, 200, 200),
    ("top_left_200x200", 10, 10, 200, 200),
    ("bottom_right_200x200", h-210, w-210, 200, 200),
    ("bottom_left_200x200", h-210, 10, 200, 200),
    # Mid-regions
    ("mid_right_200x200", h//2-100, w-210, 200, 200),
    ("mid_left_200x200", h//2-100, 10, 200, 200),
]

for name, y, x, crop_h, crop_w in crops:
    if 0 <= x < w and 0 <= y < h:
        crop = img[y:min(y+crop_h, h), x:min(x+crop_w, w)]
        if crop.size > 0:
            out_path = os.path.join(output_dir, f"{{name}}.png")
            cv2.imwrite(out_path, crop)
            print(f"Saved: {{out_path}}")

print(f"Generated {{len(crops)}} crop candidates in {{output_dir}}")
"""

    try:
        result = subprocess.run(
            ["python3", "-c", script], capture_output=True, text=True, timeout=60
        )

        if result.returncode == 0:
            return f"""## Crop Candidates

**Input**: {input_path}
**Output**: {output_dir}

**Status**: Success

```
{result.stdout}
```
"""
        else:
            return f"""## Crop Candidates

**Input**: {input_path}
**Output**: {output_dir}

**Status**: Failed

**Error**:
```
{result.stderr}
```

Note: Requires OpenCV (pip install opencv-python)
"""
    except FileNotFoundError:
        return f"""## Crop Candidates

**Status**: Error

Python3 not found.
"""
    except Exception as e:
        return f"""## Crop Candidates

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("/tmp/screenshot.png", "/tmp/qr_crops"))

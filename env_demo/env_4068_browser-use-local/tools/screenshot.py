"""
Screenshot Tool - Take a screenshot of the current page

Capture a screenshot from the browser session.
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "screenshot",
    "description": "Take a screenshot of the current browser page. "
    "This is the most reliable debugging primitive - always works even when state is empty. "
    "Use for visual verification, debugging, and extracting QR codes from login pages.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to save the screenshot (e.g., '/tmp/page.png')",
            },
            "session": {"type": "string", "default": "default", "description": "Session name"},
            "browser": {"type": "string", "default": "chromium", "description": "Browser to use"},
        },
        "required": ["path"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(path: str, session: str = "default", browser: str = "chromium") -> str:
    """
    Take a screenshot

    Args:
        path: Path to save screenshot
        session: Session name
        browser: Browser to use

    Returns:
        Confirmation message
    """
    try:
        cmd = [BROWSER_USE_CLI, "--session", session, "--browser", browser, "screenshot", path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            return f"""## Screenshot Captured

**Path**: {path}
**Session**: {session}

**Status**: Success

Screenshot saved to: {path}
"""
        else:
            return f"""## Screenshot Failed

**Path**: {path}
**Session**: {session}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## Screenshot

**Status**: Timeout

Operation timed out after 30 seconds.
"""
    except FileNotFoundError:
        return f"""## Screenshot

**Status**: Error

browser-use CLI not found.
"""
    except Exception as e:
        return f"""## Screenshot

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("/tmp/test.png"))

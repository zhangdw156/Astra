"""
Open URL Tool - Open a URL in browser session

Open a URL in a persistent browser session using browser-use CLI.
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "open_url",
    "description": "Open a URL in a browser session. Use this to navigate to a webpage. "
    "Supports persistent sessions for multi-step flows. "
    "The browser-use CLI must be installed and a supported browser (chromium) must be available.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to open (e.g., 'https://example.com', 'https://github.com/login')",
            },
            "session": {
                "type": "string",
                "default": "default",
                "description": "Session name for persistent browser state",
            },
            "browser": {
                "type": "string",
                "default": "chromium",
                "description": "Browser to use (chromium, firefox, etc.)",
            },
        },
        "required": ["url"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(url: str, session: str = "default", browser: str = "chromium") -> str:
    """
    Open a URL in browser session

    Args:
        url: URL to open
        session: Session name for persistent state
        browser: Browser to use

    Returns:
        Formatted result with URL and status
    """
    try:
        cmd = [BROWSER_USE_CLI, "--session", session, "--browser", browser, "open", url]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            return f"""## Browser: Open URL

**URL**: {url}
**Session**: {session}
**Browser**: {browser}

**Status**: Success

```
{result.stdout}
```
"""
        else:
            return f"""## Browser: Open URL

**URL**: {url}
**Session**: {session}
**Browser**: {browser}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## Browser: Open URL

**URL**: {url}

**Status**: Timeout

The operation timed out after 60 seconds.
"""
    except FileNotFoundError:
        return f"""## Browser: Open URL

**Status**: Error

browser-use CLI not found. Please ensure it's installed and in PATH.
Install with: pip install browser-use
"""
    except Exception as e:
        return f"""## Browser: Open URL

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("https://example.com"))

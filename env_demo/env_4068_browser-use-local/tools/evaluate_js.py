"""
Evaluate JS Tool - Execute JavaScript in the browser

Run arbitrary JavaScript in the context of the current page.
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "evaluate_js",
    "description": "Evaluate JavaScript in the browser context. "
    "Useful for lightweight DOM queries when get_state returns empty elements. "
    "Can query location.href, document.title, or any DOM property.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "JavaScript code to execute (e.g., 'location.href', 'document.title')",
            },
            "session": {"type": "string", "default": "default", "description": "Session name"},
            "browser": {"type": "string", "default": "chromium", "description": "Browser to use"},
        },
        "required": ["script"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(script: str, session: str = "default", browser: str = "chromium") -> str:
    """
    Evaluate JavaScript

    Args:
        script: JavaScript code to run
        session: Session name
        browser: Browser to use

    Returns:
        Script execution result
    """
    try:
        cmd = [
            BROWSER_USE_CLI,
            "--session",
            session,
            "--browser",
            browser,
            "--json",
            "eval",
            script,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                eval_result = data.get("data", {}).get("result", "")

                return f"""## JavaScript Evaluation

**Script**: {script}
**Session**: {session}

**Result**:
```
{eval_result}
```
"""
            except json.JSONDecodeError:
                return f"""## JavaScript Evaluation

**Script**: {script}

**Raw Output**:
```
{result.stdout}
```
"""
        else:
            return f"""## JavaScript Evaluation

**Script**: {script}
**Session**: {session}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## JavaScript Evaluation

**Status**: Timeout
"""
    except FileNotFoundError:
        return f"""## JavaScript Evaluation

**Status**: Error

browser-use CLI not found.
"""
    except Exception as e:
        return f"""## JavaScript Evaluation

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("document.title"))

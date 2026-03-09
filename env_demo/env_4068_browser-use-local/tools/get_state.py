"""
Get State Tool - Get browser session state

Get the current browser state including URL, title, and elements.
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "get_state",
    "description": "Get the current browser state including URL, title, and DOM elements. "
    "Use this to inspect the current page state. "
    "Note: Sometimes returns 0 elements on heavy/JS sites - use get_html as fallback.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session": {
                "type": "string",
                "default": "default",
                "description": "Session name to get state from",
            },
            "browser": {"type": "string", "default": "chromium", "description": "Browser to use"},
        },
        "required": [],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(session: str = "default", browser: str = "chromium") -> str:
    """
    Get browser state

    Args:
        session: Session name
        browser: Browser to use

    Returns:
        Formatted state information
    """
    try:
        cmd = [BROWSER_USE_CLI, "--session", session, "--browser", browser, "--json", "state"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                state = data.get("data", {})

                url = state.get("url", "N/A")
                title = state.get("title", "N/A")
                elements_count = len(state.get("elements", []))

                output = f"""## Browser State

**Session**: {session}
**URL**: {url}
**Title**: {title}
**Elements**: {elements_count}

### Element Preview
"""

                elements = state.get("elements", [])[:10]
                for i, el in enumerate(elements, 1):
                    tag = el.get("tag", "?")
                    text = el.get("text", "")[:50]
                    output += f"{i}. <{tag}> {text}\n"

                if elements_count > 10:
                    output += f"\n... and {elements_count - 10} more elements"

                return output
            except json.JSONDecodeError:
                return f"""## Browser State

**Session**: {session}

**Raw Output**:
```
{result.stdout}
```
"""
        else:
            return f"""## Browser State

**Session**: {session}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## Browser State

**Session**: {session}

**Status**: Timeout
"""
    except FileNotFoundError:
        return f"""## Browser State

**Status**: Error

browser-use CLI not found.
"""
    except Exception as e:
        return f"""## Browser State

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute())

"""
Get HTML Tool - Get page HTML

Extract the full HTML content from the current page.
"""

import json
import os
import re
import subprocess

TOOL_SCHEMA = {
    "name": "get_html",
    "description": "Get the full HTML content of the current page. "
    "Works even when get_state returns 0 elements. "
    "Use for link discovery, extracting data:image base64 images, and DOM analysis.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session": {"type": "string", "default": "default", "description": "Session name"},
            "browser": {"type": "string", "default": "chromium", "description": "Browser to use"},
        },
        "required": [],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")


def execute(session: str = "default", browser: str = "chromium") -> str:
    """
    Get page HTML

    Args:
        session: Session name
        browser: Browser to use

    Returns:
        HTML content with extracted URLs
    """
    try:
        cmd = [BROWSER_USE_CLI, "--session", session, "--browser", browser, "--json", "get", "html"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                html = data.get("data", {}).get("html", "")

                # Extract URLs from HTML
                urls = set(re.findall(r"https?://[^\s\"'<>]+", html))
                relevant_urls = [
                    u
                    for u in urls
                    if any(k in u for k in ["demo", "login", "console", "qr", "qrcode", "auth"])
                ]

                output = f"""## Page HTML

**Session**: {session}
**HTML Length**: {len(html)} characters

### Extracted URLs (filtered)
"""

                if relevant_urls:
                    for url in relevant_urls[:20]:
                        output += f"- {url}\n"
                else:
                    output += "No relevant URLs found (demo, login, console, qr, auth)\n"

                output += f"\n### All URLs ({len(urls)} total)\n"
                for url in sorted(list(urls)[:30]):
                    output += f"- {url}\n"

                if len(urls) > 30:
                    output += f"... and {len(urls) - 30} more\n"

                return output

            except json.JSONDecodeError:
                return f"""## Page HTML

**Session**: {session}

**Raw Output**:
```
{result.stdout[:2000]}
```
"""
        else:
            return f"""## Page HTML

**Session**: {session}

**Status**: Failed

**Error**:
```
{result.stderr}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## Page HTML

**Status**: Timeout
"""
    except FileNotFoundError:
        return f"""## Page HTML

**Status**: Error

browser-use CLI not found.
"""
    except Exception as e:
        return f"""## Page HTML

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute())

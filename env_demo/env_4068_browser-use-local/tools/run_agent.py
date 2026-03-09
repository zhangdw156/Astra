"""
Run Agent Tool - Run browser-use agent with custom LLM

Run the browser-use agent with an OpenAI-compatible LLM (e.g., Moonshot/Kimi).
"""

import json
import os
import subprocess

TOOL_SCHEMA = {
    "name": "run_agent",
    "description": "Run the browser-use agent with an OpenAI-compatible LLM. "
    "Use for complex multi-step browser automation tasks. "
    "Supports custom LLM base URLs (e.g., Moonshot/Kimi at https://api.moonshot.cn/v1). "
    "Requires OPENAI_API_KEY and OPENAI_BASE_URL environment variables.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "Task goal for the agent (e.g., 'Find the login QR code on the page')",
            },
            "session": {
                "type": "string",
                "default": "agent",
                "description": "Session name for the agent",
            },
            "model": {
                "type": "string",
                "default": "kimi-k2.5",
                "description": "Model to use (e.g., 'kimi-k2.5', 'gpt-4o')",
            },
            "max_steps": {
                "type": "integer",
                "default": 10,
                "description": "Maximum number of steps the agent can take",
            },
        },
        "required": ["goal"],
    },
}

BROWSER_USE_CLI = os.environ.get("BROWSER_USE_CLI", "browser-use")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")


def execute(
    goal: str, session: str = "agent", model: str = "kimi-k2.5", max_steps: int = 10
) -> str:
    """
    Run browser-use agent

    Args:
        goal: Task goal for the agent
        session: Session name
        model: Model to use
        max_steps: Maximum steps

    Returns:
        Agent execution results
    """
    if not OPENAI_API_KEY:
        return f"""## Run Agent

**Status**: Error

OPENAI_API_KEY environment variable is not set.
Please set it to your API key (e.g., Moonshot/Kimi API key).
"""

    try:
        # Build the agent command
        # This assumes a Python script approach for agent runs
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = OPENAI_API_KEY
        env["OPENAI_BASE_URL"] = OPENAI_BASE_URL

        cmd = [
            "python3",
            "-c",
            f"""
import asyncio
from browser_use import Agent, BrowserConfig
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="{model}",
    api_key="{OPENAI_API_KEY}",
    base_url="{OPENAI_BASE_URL}",
    temperature=1.0,
    frequency_penalty=0.0,
)

async def run():
    agent = Agent(
        llm=llm,
        browser_config=BrowserConfig(headless=False),
    )
    result = await agent.run("{goal}")
    print(result)

asyncio.run(run())
""",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)

        if result.returncode == 0:
            return f"""## Browser Agent

**Goal**: {goal}
**Session**: {session}
**Model**: {model}

**Status**: Completed

**Output**:
```
{result.stdout[:2000]}
```
"""
        else:
            return f"""## Browser Agent

**Goal**: {goal}
**Session**: {session}
**Model**: {model}

**Status**: Failed

**Error**:
```
{result.stderr[:2000]}
```
"""

    except subprocess.TimeoutExpired:
        return f"""## Browser Agent

**Goal**: {goal}

**Status**: Timeout

The operation timed out after 5 minutes.
"""
    except Exception as e:
        return f"""## Browser Agent

**Status**: Error

{str(e)}
"""


if __name__ == "__main__":
    print(execute("Go to example.com and take a screenshot"))

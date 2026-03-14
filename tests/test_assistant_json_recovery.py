from __future__ import annotations

from astra.agent._assistant_agent.agent import AssistantAgent
from astra.agent._assistant_agent.config import AssistantAgentConfig


def test_assistant_json_patch_recovers_malformed_tool_call_object() -> None:
    from qwen_agent.llm.fncall_prompts import nous_fncall_prompt as module

    original_loads = module.json5.loads
    agent = AssistantAgent(AssistantAgentConfig(mcp_url="http://127.0.0.1:9999/sse"))

    try:
        agent.patch_nous_fncall_json_parsing()
        parsed = module.json5.loads(
            '<tool_call>\n'
            '{"name": "skill-tools-grep", "arguments": {"pattern": "helper", "path": "src"}\n'
            '</tool_call>'
        )
    finally:
        module.json5.loads = original_loads

    assert parsed["name"] == "skill-tools-grep"
    assert parsed["arguments"]["pattern"] == "helper"
    assert parsed["arguments"]["path"] == "src"

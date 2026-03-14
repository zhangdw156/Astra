from __future__ import annotations

import sys
import types

from astra.agent._assistant_agent.agent import (
    ASSISTANT_SYSTEM_PROMPT,
    AssistantAgent,
)
from astra.agent._assistant_agent.config import AssistantAgentConfig


def test_assistant_system_prompt_includes_grounding_and_unsupported_tool_rules() -> None:
    assert "If the available tools do not support the user's requested calculation or action, say so clearly." in ASSISTANT_SYSTEM_PROMPT
    assert "Do not invent numbers" in ASSISTANT_SYSTEM_PROMPT
    assert "do not produce a made-up estimate" in ASSISTANT_SYSTEM_PROMPT
    assert "giving the user a natural-language answer" in ASSISTANT_SYSTEM_PROMPT


def test_assistant_create_passes_system_prompt_to_qwen_agent(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAssistant:
        def __init__(self, *, llm, system_message, function_list):
            captured["llm"] = llm
            captured["system_message"] = system_message
            captured["function_list"] = function_list
            self.function_map = {}

    fake_agents = types.ModuleType("qwen_agent.agents")
    fake_agents.Assistant = FakeAssistant
    monkeypatch.setitem(sys.modules, "qwen_agent.agents", fake_agents)

    agent = AssistantAgent(
        AssistantAgentConfig(
            mcp_url="http://127.0.0.1:18000/sse",
            enable_mcp_patch=False,
            enable_json_patch=False,
        )
    )
    agent.create()

    assert captured["system_message"] == ASSISTANT_SYSTEM_PROMPT
    assert "Do not invent numbers" in str(captured["system_message"])
    assert "tool-using multi-turn conversation" in str(captured["system_message"])

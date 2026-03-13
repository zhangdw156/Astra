from __future__ import annotations

import json
from typing import Any

from ...agent._tool_agent import ToolAgent, ToolAgentConfig
from ...envs import BackendExecutionResult


class LLMToolExecutor:
    def __init__(self, *, tool_agent_config: ToolAgentConfig):
        self.tool_agent = ToolAgent(tool_agent_config)

    def execute_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        state_key: str,
        tool_schema: dict[str, Any] | None = None,
        available_tools: list[dict[str, Any]] | None = None,
        conversation_context: str | None = None,
    ) -> BackendExecutionResult:
        before_state = self.get_state(state_key)
        result = self.tool_agent.generate_response(
            tool_name=tool_name,
            arguments_json=json.dumps(arguments, ensure_ascii=False),
            session_state=before_state,
            conversation_context=conversation_context,
            tool_schema=tool_schema,
            available_tools=available_tools,
        )

        if result.state is not None:
            self.tool_agent.set_state(result.state, state_key)

        after_state = self.get_state(state_key)
        response = (result.response or "").strip() or json.dumps(
            {"status": "executed", "tool": tool_name},
            ensure_ascii=False,
        )

        parsed_result: dict[str, Any]
        try:
            parsed = json.loads(response)
            parsed_result = parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            parsed_result = {"raw": response}

        return BackendExecutionResult(
            response_text=response,
            result=parsed_result,
            before_state=before_state,
            after_state=after_state,
        )

    def reset_state(self, state_key: str) -> None:
        self.tool_agent.set_state({}, state_key)

    def get_state(self, state_key: str) -> dict[str, Any]:
        return self.tool_agent.get_state(state_key)

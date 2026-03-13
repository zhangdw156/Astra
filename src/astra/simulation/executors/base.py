from __future__ import annotations

from typing import Any, Protocol

from ...envs import BackendExecutionResult


class ToolExecutor(Protocol):
    def execute_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        state_key: str,
        tool_schema: dict[str, Any] | None = None,
        available_tools: list[dict[str, Any]] | None = None,
        conversation_context: str | None = None,
    ) -> BackendExecutionResult: ...

    def reset_state(self, state_key: str) -> None: ...
    def get_state(self, state_key: str) -> dict[str, Any]: ...

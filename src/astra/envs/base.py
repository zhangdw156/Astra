from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

StateDict = dict[str, Any]
ToolArguments = dict[str, Any]


class SkillBackendProtocol(Protocol):
    def load_scenario(self, scenario: dict[str, Any]) -> None: ...
    def reset(self) -> None: ...
    def call(
        self,
        tool_name: str,
        arguments: ToolArguments,
        conversation_context: str | None = None,
    ) -> dict[str, Any]: ...
    def snapshot_state(self) -> StateDict: ...
    def visible_state(self) -> StateDict: ...


@dataclass(slots=True)
class BackendExecutionResult:
    response_text: str
    result: dict[str, Any]
    before_state: StateDict
    after_state: StateDict

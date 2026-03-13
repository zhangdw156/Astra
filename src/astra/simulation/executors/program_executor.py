from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...envs import (
    BackendExecutionResult,
    LoadedBackend,
    load_backend_from_skill_dir,
    validate_hybrid_result,
)


class ProgramToolExecutor:
    def __init__(self, *, skill_dir: Path):
        loaded = load_backend_from_skill_dir(skill_dir)
        if loaded is None:
            raise FileNotFoundError(
                f"No executable backend found under skill dir: {skill_dir}"
            )

        self.skill_dir = skill_dir.resolve()
        self.loaded_backend = loaded

    @property
    def profile(self):
        return self.loaded_backend.profile

    @property
    def scenario_id(self) -> str:
        return self.loaded_backend.scenario_spec.scenario_id

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
        del state_key, tool_schema, available_tools
        before_state = self.get_state("")
        result = self.loaded_backend.backend.call(
            tool_name=tool_name,
            arguments=arguments,
            conversation_context=conversation_context,
        )
        validate_hybrid_result(profile=self.profile, result=result)
        after_state = self.get_state("")
        response_text = json.dumps(result, ensure_ascii=False)

        return BackendExecutionResult(
            response_text=response_text,
            result=result,
            before_state=before_state,
            after_state=after_state,
        )

    def reset_state(self, state_key: str) -> None:
        del state_key
        self.loaded_backend.backend.reset()
        self.loaded_backend.backend.load_scenario(self.loaded_backend.scenario)

    def get_state(self, state_key: str) -> dict[str, Any]:
        del state_key
        return self.loaded_backend.backend.snapshot_state()

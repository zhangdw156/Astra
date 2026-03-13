from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class EvalAgentPromptBuilder:
    """
    负责构造 EvalAgent 的评估 prompt。

    当前支持的占位符：
    - {BLUEPRINT_JSON}
    - {TRAJECTORY_JSON}
    """

    BLUEPRINT_ALLOWED_KEYS = {
        "blueprint_id",
        "skill_name",
        "persona_id",
        "created_at",
        "goals",
        "possible_tool_calls",
        "scenario_id",
        "environment_profile",
        "initial_state",
        "expected_final_state",
        "state_checkpoints",
        "user_agent_config",
        "end_condition",
    }

    TRAJECTORY_ALLOWED_KEYS = {
        "run_id",
        "trajectory_id",
        "blueprint_id",
        "skill_name",
        "persona_id",
        "tools",
        "messages",
        "structured_turns",
        "validation",
        "final_tool_state",
        "initial_state",
        "scenario_id",
        "environment_profile",
        "state_transitions",
    }

    def __init__(
        self,
        prompt_path: Path,
        max_message_chars: int | None = None,
    ):
        self.prompt_path = prompt_path
        self.max_message_chars = max_message_chars
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def sanitize_trajectory_for_eval(self, trajectory: dict[str, Any]) -> dict[str, Any]:
        """
        清理 trajectory，保留 evaluator 真正需要看到的字段。

        当前规则：
        - 仅保留白名单字段
        - 递归删除 reasoning_content
        - 若 max_message_chars 配置存在，对超长字符串做截断
        """
        filtered = {
            key: value
            for key, value in trajectory.items()
            if key in self.TRAJECTORY_ALLOWED_KEYS
        }
        return self._sanitize_obj(filtered)

    def sanitize_blueprint_for_eval(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        """
        清理 blueprint，保留 evaluator 真正需要看到的字段。

        当前规则：
        - 仅保留白名单字段
        - 若 max_message_chars 配置存在，对超长字符串做截断
        """
        filtered = {
            key: value
            for key, value in blueprint.items()
            if key in self.BLUEPRINT_ALLOWED_KEYS
        }
        return self._sanitize_obj(filtered)

    def build(
        self,
        *,
        blueprint: dict[str, Any],
        trajectory: dict[str, Any],
    ) -> str:
        """
        构造最终评估 prompt。
        """
        clean_blueprint = self.sanitize_blueprint_for_eval(blueprint)
        clean_trajectory = self.sanitize_trajectory_for_eval(trajectory)

        prompt = self.template_text
        prompt = prompt.replace(
            "{BLUEPRINT_JSON}",
            json.dumps(clean_blueprint, ensure_ascii=False, indent=2),
        )
        prompt = prompt.replace(
            "{TRAJECTORY_JSON}",
            json.dumps(clean_trajectory, ensure_ascii=False, indent=2),
        )
        return prompt

    def _sanitize_obj(self, obj: Any) -> Any:
        """
        递归清理对象。
        """
        if isinstance(obj, dict):
            clean: dict[str, Any] = {}
            for key, value in obj.items():
                if key == "reasoning_content":
                    continue
                clean[key] = self._sanitize_obj(value)
            return clean

        if isinstance(obj, list):
            return [self._sanitize_obj(item) for item in obj]

        if isinstance(obj, str):
            if self.max_message_chars is not None and len(obj) > self.max_message_chars:
                return obj[: self.max_message_chars] + "\n... [truncated]"
            return obj

        return obj

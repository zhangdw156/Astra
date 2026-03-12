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
        递归清理 trajectory，去掉不应暴露给 evaluator 的字段。
        当前规则：
        - 删除 reasoning_content
        - 若 max_message_chars 配置存在，对超长字符串做截断
        """
        return self._sanitize_obj(trajectory)

    def sanitize_blueprint_for_eval(self, blueprint: dict[str, Any]) -> dict[str, Any]:
        """
        目前 blueprint 原样使用，仅对超长字符串做可选截断。
        """
        return self._sanitize_obj(blueprint)

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
            return [self._sanitize_obj(x) for x in obj]

        if isinstance(obj, str):
            if self.max_message_chars is not None and len(obj) > self.max_message_chars:
                return obj[: self.max_message_chars] + "\n... [truncated]"
            return obj

        return obj
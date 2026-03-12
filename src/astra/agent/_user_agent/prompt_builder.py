from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class UserAgentPromptBuilder:
    """
    负责基于模板渲染 user-agent prompt。
    """

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def build(
        self,
        *,
        goals: list[str],
        current_goal_index: int,
        user_message_count: int,
        user_agent_config: dict[str, Any],
        conversation_history: str,
        end_condition: str,
    ) -> str:
        """
        使用已准备好的内容渲染 prompt。
        """
        num_goals = len(goals)
        current_goal_text = (
            goals[current_goal_index - 1]
            if 1 <= current_goal_index <= num_goals
            else "(无目标)"
        )
        goals_str = (
            "\n".join(f"{i}. {g}" for i, g in enumerate(goals, 1))
            if goals
            else "(无目标)"
        )

        prompt = self.template_text
        prompt = prompt.replace("{GOALS}", goals_str.strip())
        prompt = prompt.replace("{NUM_GOALS}", str(num_goals))
        prompt = prompt.replace("{USER_MESSAGE_COUNT}", str(user_message_count))
        prompt = prompt.replace("{CURRENT_GOAL_INDEX}", str(current_goal_index))
        prompt = prompt.replace("{CURRENT_GOAL_TEXT}", current_goal_text)
        prompt = prompt.replace(
            "{USER_AGENT_CONFIG}",
            json.dumps(user_agent_config or {}, ensure_ascii=False),
        )
        prompt = prompt.replace("{CONVERSATION_HISTORY}", conversation_history)
        prompt = prompt.replace("{END_CONDITION}", end_condition or "")

        return prompt
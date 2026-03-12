from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from ...utils import config as astra_config
from ...utils import logger

from .config import UserAgentConfig
from .prompt_builder import UserAgentPromptBuilder
from .types import UserTurnResult


TASK_END_MARKER = "[TASK_END]"


class UserAgent:
    """
    UserAgent：根据 blueprint、对话历史与当前 goal 生成下一条用户消息。

    职责：
    1. 读取并缓存 user-agent prompt 模板
    2. 根据 goals 与历史计算当前 goal
    3. 格式化对话历史
    4. 构造结构化 task memory
    5. 调用模型生成下一条用户消息
    6. 识别 [TASK_END] 并剥离 <think>
    """

    def __init__(self, config: UserAgentConfig):
        self.config = config.normalized()
        self.prompt_builder = UserAgentPromptBuilder(
            prompt_path=self.config.prompt_path,
        )

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate_message(
        self,
        *,
        blueprint: dict[str, Any],
        messages: list[dict[str, Any]],
        user_message_count: int | None = None,
    ) -> UserTurnResult:
        """
        生成下一条用户消息。

        参数：
        - blueprint: 任务蓝图
        - messages: 当前对话历史
        - user_message_count: 已发送的 user 消息数量；若不传则从 messages 自动统计
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        goals = blueprint.get("goals") or []
        if user_message_count is None:
            user_message_count = self.count_user_messages(messages)

        current_goal_index = min(user_message_count + 1, len(goals)) if goals else 1
        conversation_history = self.format_conversation_history(messages)

        prompt = self.prompt_builder.build(
            goals=goals,
            current_goal_index=current_goal_index,
            user_message_count=user_message_count,
            user_agent_config=blueprint.get("user_agent_config", {}),
            conversation_history=conversation_history,
            end_condition=blueprint.get("end_condition", ""),
        )

        raw_response = self.call_model(prompt)

        if TASK_END_MARKER in raw_response:
            return UserTurnResult(
                message=TASK_END_MARKER,
                is_task_end=True,
                raw_response=raw_response,
                thinking="",
            )

        cleaned_message, thinking = self.strip_think(raw_response)
        return UserTurnResult(
            message=cleaned_message,
            is_task_end=False,
            raw_response=raw_response,
            thinking=thinking,
        )

    def count_user_messages(self, messages: list[dict[str, Any]]) -> int:
        """
        统计对话历史中的 user 消息数量。
        """
        return sum(1 for m in messages if m.get("role") == "user")

    def format_conversation_history(self, messages: list[dict[str, Any]]) -> str:
        """
        将 messages 格式化为 User Agent 可读的对话历史。
        """
        lines: list[str] = []

        for message in messages:
            role = message.get("role", "")
            content = (message.get("content") or "").strip()

            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                if len(content) > 1500:
                    content = content[:1500] + "\n... [truncated]"
                lines.append(f"Assistant: {content}")
            elif role == "function":
                name = message.get("name", "tool")
                if len(content) > 800:
                    content = content[:800] + "\n... [truncated]"
                lines.append(f"[Tool {name}]: {content}")

        return "\n\n".join(lines) if lines else "(No messages yet)"

    def extract_pending_questions(self, messages: list[dict[str, Any]]) -> list[str]:
        """
        提取最近一条 assistant 提出的待回答问题（若有）。
        """
        for message in reversed(messages):
            if message.get("role") != "assistant":
                continue

            content = (message.get("content") or "").strip()
            if content and "?" in content:
                return [content[-300:]]
            break

        return []

    def build_structured_task_memory(
        self,
        *,
        blueprint: dict[str, Any],
        messages: list[dict[str, Any]],
        user_message_count: int,
    ) -> dict[str, Any]:
        """
        构建 User Agent 的结构化任务记忆，提升多轮行为稳定性。
        """
        goals = blueprint.get("goals") or []
        done_count = min(user_message_count, len(goals))
        done_goals = goals[:done_count]
        remaining_goals = goals[done_count:]
        pending_questions = self.extract_pending_questions(messages)

        last_assistant_action = "none"
        for message in reversed(messages):
            role = message.get("role", "")
            if role == "function":
                last_assistant_action = f"tool_called:{message.get('name', '')}"
                break
            if role == "assistant":
                text = (message.get("content") or "").strip()
                last_assistant_action = "asked_question" if "?" in text else "provided_answer"
                break

        return {
            "done_goals": done_goals,
            "remaining_goals": remaining_goals,
            "pending_questions": pending_questions,
            "last_assistant_action": last_assistant_action,
        }

    def strip_think(self, text: str) -> tuple[str, str]:
        """
        从 User Agent 的原始输出中剥离 <think>...</think>。
        返回 (用户可见消息, 思考内容)。
        """
        if not text:
            return "", ""

        pattern = r"<think>(.*?)</think>"
        thinking_parts: list[str] = []

        for match in re.finditer(pattern, text, re.DOTALL):
            thinking_parts.append(match.group(1).strip())

        if thinking_parts:
            thinking = "\n\n".join(thinking_parts)
            clean = re.sub(pattern, "", text, flags=re.DOTALL).strip()
            return clean, thinking

        return text.strip(), ""

    # -------------------------------------------------------------------------
    # LLM
    # -------------------------------------------------------------------------

    def call_model(self, prompt: str) -> str:
        """
        调用模型生成用户消息原始文本。
        """
        api_key = astra_config.get_user_agent_api_key()
        model = astra_config.get_user_agent_model()
        base_url = astra_config.get_user_agent_base_url()

        logger.info("Calling user model: {}", model)
        logger.debug("User prompt length: {} chars", len(prompt))

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        raw = (response.choices[0].message.content or "").strip()
        logger.debug("User raw response length: {} chars", len(raw))
        return raw
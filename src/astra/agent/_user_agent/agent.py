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
OPENAI_REQUEST_TIMEOUT_SEC = 120.0
GOAL_FOCUS_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "do",
    "for",
    "from",
    "get",
    "have",
    "help",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "like",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "show",
    "so",
    "that",
    "the",
    "their",
    "them",
    "there",
    "this",
    "to",
    "up",
    "us",
    "want",
    "we",
    "with",
    "you",
    "your",
}
OFF_GOAL_PIVOT_MARKERS = (
    "actually, skip",
    "skip that",
    "move on",
    "move into",
    "instead",
    "something else",
    "different topic",
    "another topic",
    "hold off",
)


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

        if goals:
            post_goal_turns = max(0, user_message_count - len(goals))
            if user_message_count >= len(goals):
                if (
                    post_goal_turns >= self.config.max_post_goal_follow_up_turns
                    or not self.assistant_requested_follow_up(messages)
                ):
                    return UserTurnResult(
                        message=TASK_END_MARKER,
                        is_task_end=True,
                        raw_response=TASK_END_MARKER,
                        thinking="",
                    )

        current_goal_index = min(user_message_count + 1, len(goals)) if goals else 1
        current_goal_text = (
            goals[current_goal_index - 1]
            if goals and 1 <= current_goal_index <= len(goals)
            else ""
        )
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
        cleaned_message, thinking = self.strip_think(raw_response)

        task_end_result = self.parse_task_end_marker(
            message=cleaned_message,
            goals=goals,
            user_message_count=user_message_count,
        )
        if task_end_result is not None:
            return UserTurnResult(
                message=task_end_result["message"],
                is_task_end=task_end_result["is_task_end"],
                raw_response=raw_response,
                thinking=thinking,
            )

        cleaned_message = self.normalize_user_message(cleaned_message)
        if self.should_fallback_to_current_goal(
            message=cleaned_message,
            current_goal_text=current_goal_text,
            messages=messages,
            user_message_count=user_message_count,
        ):
            logger.warning(
                "UserAgent message drifted from current goal {}; using fallback",
                current_goal_index,
            )
            cleaned_message = self.build_goal_fallback_message(
                current_goal_text=current_goal_text,
                messages=messages,
            )

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

    def parse_task_end_marker(
        self,
        *,
        message: str,
        goals: list[Any],
        user_message_count: int,
    ) -> dict[str, Any] | None:
        """
        识别 UserAgent 输出中的 [TASK_END]。

        兼容两种情况：
        - 纯 marker：直接结束
        - 混在自然语言中：若 goals 已经全部推进过，则按结束处理，避免多跑一轮
        """
        normalized = (message or "").strip()
        if not normalized or TASK_END_MARKER not in normalized:
            return None

        if normalized == TASK_END_MARKER:
            return {"message": TASK_END_MARKER, "is_task_end": True}

        before, _, after = normalized.partition(TASK_END_MARKER)
        visible_text = f"{before.strip()} {after.strip()}".strip()
        if user_message_count >= len(goals):
            logger.info("UserAgent embedded [TASK_END] in prose; treating it as task end")
            return {"message": TASK_END_MARKER, "is_task_end": True}

        return {"message": visible_text or normalized, "is_task_end": False}

    def assistant_requested_follow_up(self, messages: list[dict[str, Any]]) -> bool:
        """
        判断上一条 assistant 消息是否明确在索要补充信息。
        """
        for message in reversed(messages):
            if message.get("role") != "assistant":
                continue
            content = (message.get("content") or "").strip().lower()
            if not content:
                return False
            if "?" in content:
                return True
            follow_up_markers = (
                "could you",
                "can you",
                "please provide",
                "please share",
                "let me know",
                "which one",
                "what file",
                "what path",
                "what value",
                "do you want",
                "would you like",
            )
            return any(marker in content for marker in follow_up_markers)
        return False

    def normalize_user_message(self, message: str) -> str:
        """
        轻量清理用户消息，避免明显脚本化占位符。
        """
        normalized = (message or "").strip()
        normalized = re.sub(
            r"\[(my|our|your)\s+([^\[\]]+)\]",
            r"\1 \2",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def should_fallback_to_current_goal(
        self,
        *,
        message: str,
        current_goal_text: str,
        messages: list[dict[str, Any]],
        user_message_count: int,
    ) -> bool:
        normalized = (message or "").strip()
        if not normalized:
            return True

        goal_tokens = self.extract_focus_tokens(current_goal_text)
        message_tokens = self.extract_focus_tokens(normalized)
        goal_overlap = len(goal_tokens & message_tokens)
        lowered = normalized.lower()

        if user_message_count == 0 and goal_tokens and goal_overlap == 0:
            return True

        if any(marker in lowered for marker in OFF_GOAL_PIVOT_MARKERS) and goal_overlap == 0:
            return True

        last_assistant = self.get_last_assistant_message(messages)
        if last_assistant:
            assistant_tokens = self.extract_focus_tokens(last_assistant)
            if "?" in last_assistant and goal_overlap == 0 and not (assistant_tokens & message_tokens):
                return True

        if goal_tokens and goal_overlap == 0 and len(message_tokens) >= 8:
            return True

        return False

    def build_goal_fallback_message(
        self,
        *,
        current_goal_text: str,
        messages: list[dict[str, Any]],
    ) -> str:
        last_assistant = self.get_last_assistant_message(messages)
        if last_assistant and "?" in last_assistant:
            return f"For this step, let's stay focused on this: {current_goal_text}"
        return f"Let's focus on this next part: {current_goal_text}"

    def get_last_assistant_message(self, messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "assistant":
                return (message.get("content") or "").strip()
        return ""

    def extract_focus_tokens(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (text or "").lower())
        return {token for token in tokens if token not in GOAL_FOCUS_STOPWORDS}

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

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=OPENAI_REQUEST_TIMEOUT_SEC,
            max_retries=2,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        raw = (response.choices[0].message.content or "").strip()
        logger.debug("User raw response length: {} chars", len(raw))
        return raw

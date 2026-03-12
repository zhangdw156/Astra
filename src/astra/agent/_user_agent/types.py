from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserTurnResult:
    """
    UserAgent 单次生成结果。
    """

    message: str
    is_task_end: bool
    raw_response: str
    thinking: str = ""
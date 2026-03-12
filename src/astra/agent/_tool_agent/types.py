from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolExecutionResult:
    """
    单次工具调用生成结果。
    """

    response: str
    state: dict[str, Any]
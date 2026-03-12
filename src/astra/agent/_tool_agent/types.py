from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolExecutionResult:
    """
    单次工具调用生成结果。

    state:
    - dict: 模型给出了有效的新状态
    - None: 未给出有效状态，不应覆盖旧状态
    """

    response: str
    state: dict[str, Any] | None
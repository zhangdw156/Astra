from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvalAgentConfig:
    """
    EvalAgent 的运行配置。

    说明：
    - prompt_path: eval agent 提示词模板路径
    - model_temperature: 调用模型时的温度参数
    - verbose: 是否输出更详细日志
    - max_message_chars: 可选，对超长字符串字段做截断，控制评估成本；None 表示不截断
    """

    prompt_path: Path
    model_temperature: float = 0.2
    verbose: bool = False
    max_message_chars: int | None = None

    def normalized(self) -> "EvalAgentConfig":
        """
        将路径规范化为绝对路径，返回新的配置对象。
        """
        return EvalAgentConfig(
            prompt_path=self.prompt_path.resolve(),
            model_temperature=self.model_temperature,
            verbose=self.verbose,
            max_message_chars=self.max_message_chars,
        )

    def validate_basic(self) -> list[str]:
        """
        仅做轻量配置校验。
        """
        errors: list[str] = []

        if not (0.0 <= self.model_temperature <= 2.0):
            errors.append(
                f"model_temperature 必须在 [0.0, 2.0] 范围内: {self.model_temperature}"
            )

        if self.max_message_chars is not None and self.max_message_chars <= 0:
            errors.append(
                f"max_message_chars 必须为正整数或 None: {self.max_message_chars}"
            )

        return errors
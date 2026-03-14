from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class UserAgentConfig:
    """
    UserAgent 的运行配置。

    说明：
    - prompt_path: user agent 提示词模板路径
    - model_temperature: 调用模型时的温度参数
    - verbose: 是否输出更详细日志
    """

    prompt_path: Path
    model_temperature: float = 0.5
    verbose: bool = False
    max_post_goal_follow_up_turns: int = 3

    def normalized(self) -> "UserAgentConfig":
        """
        将路径规范化为绝对路径，返回新的配置对象。
        """
        return UserAgentConfig(
            prompt_path=self.prompt_path.resolve(),
            model_temperature=self.model_temperature,
            verbose=self.verbose,
            max_post_goal_follow_up_turns=self.max_post_goal_follow_up_turns,
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
        if self.max_post_goal_follow_up_turns < 0:
            errors.append(
                "max_post_goal_follow_up_turns 不能小于 0: "
                f"{self.max_post_goal_follow_up_turns}"
            )

        return errors

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssistantAgentConfig:
    """
    AssistantAgent 的运行配置。

    说明：
    - mcp_url: MCP SSE 服务地址
    - verbose: 是否输出更详细日志
    - enable_mcp_patch: 是否启用 MCP 参数容错 patch
    - enable_json_patch: 是否启用 qwen-agent JSON 解析容错 patch
    """

    mcp_url: str
    verbose: bool = False
    enable_mcp_patch: bool = True
    enable_json_patch: bool = True
    request_timeout_sec: float = 120.0
    max_retries: int = 2
    max_llm_calls_per_run: int = 6

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if not self.mcp_url.strip():
            errors.append("mcp_url 不能为空")
        if self.request_timeout_sec <= 0:
            errors.append("request_timeout_sec 必须为正数")
        if self.max_retries < 0:
            errors.append("max_retries 不能小于 0")
        if self.max_llm_calls_per_run <= 0:
            errors.append("max_llm_calls_per_run 必须为正整数")

        return errors

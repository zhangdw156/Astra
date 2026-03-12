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

    def validate_basic(self) -> list[str]:
        errors: list[str] = []

        if not self.mcp_url.strip():
            errors.append("mcp_url 不能为空")

        return errors
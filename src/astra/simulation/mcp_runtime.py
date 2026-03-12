from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from ..agent._tool_agent import ToolAgent, ToolAgentConfig
from ..utils import logger

from .config import MCPRuntimeConfig


class LocalMCPRuntime:
    """
    本地轻量 MCP runtime。

    设计目标：
    - 基于 ToolAgent + tools.jsonl 在当前进程内注册 FastMCP 工具
    - 以 SSE 暴露给 AssistantAgent
    - 支持在一个 batch 内复用
    - ToolAgent 状态保留在当前进程，可直接读取 final_tool_state
    """

    def __init__(
        self,
        *,
        config: MCPRuntimeConfig,
        tool_agent_config: ToolAgentConfig,
        tools_path: Path,
        state_key: str,
    ):
        self.config = config
        self.tools_path = tools_path.resolve()
        self.state_key = state_key

        self.tool_agent = ToolAgent(tool_agent_config)
        self.tools = self.tool_agent.load_tools_from_jsonl(self.tools_path)

        self._mcp: Any | None = None
        self._thread: threading.Thread | None = None
        self._started = False

    @property
    def url(self) -> str:
        return self.config.url

    @property
    def tool_name_signature(self) -> tuple[str, ...]:
        names = []
        for tool in self.tools:
            name = tool.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return tuple(sorted(names))

    def is_reachable(self) -> bool:
        try:
            with urlopen(self.url, timeout=2):
                return True
        except Exception:
            return False

    def start(self) -> None:
        """
        启动本地 MCP SSE runtime。
        """
        if self._started:
            return

        if self.is_reachable():
            raise RuntimeError(
                f"MCP URL 在 runtime 启动前已可达，可能端口被占用: {self.url}"
            )

        from fastmcp import FastMCP

        self._mcp = FastMCP(self.config.server_name)
        self.tool_agent.create_mcp_tools(
            mcp=self._mcp,
            tools=self.tools,
            state_key=self.state_key,
        )

        self._thread = threading.Thread(
            target=self._serve,
            name="astra-local-mcp-runtime",
            daemon=True,
        )
        self._thread.start()

        deadline = time.time() + self.config.start_timeout_sec
        while time.time() < deadline:
            if self.is_reachable():
                self._started = True
                logger.info("Local MCP runtime started at {}", self.url)
                return
            time.sleep(self.config.poll_interval_sec)

        raise RuntimeError(f"本地 MCP runtime 启动超时: {self.url}")

    def stop(self) -> None:
        """
        尝试关闭本地 MCP runtime。

        说明：
        - 若底层 FastMCP 暴露 shutdown / stop / close，则调用
        - 若未暴露显式关闭 API，则依赖守护线程随进程退出结束
        """
        if not self._started:
            return

        if self._mcp is not None:
            for method_name in ("shutdown", "stop", "close"):
                method = getattr(self._mcp, method_name, None)
                if callable(method):
                    try:
                        method()
                    except Exception as exc:
                        logger.warning(
                            "Stopping local MCP runtime via {} failed: {}",
                            method_name,
                            exc,
                        )
                    break

        self._started = False
        logger.info("Local MCP runtime stopped (best effort)")

    def reset_state(self, key: str | None = None) -> None:
        """
        重置某个 state 分区。
        """
        target_key = key or self.state_key
        self.tool_agent.set_state({}, target_key)

    def get_state(self, key: str | None = None) -> dict[str, Any]:
        """
        获取某个 state 分区。
        """
        target_key = key or self.state_key
        return self.tool_agent.get_state(target_key)

    def _serve(self) -> None:
        """
        后台启动 FastMCP 服务。
        """
        if self._mcp is None:
            return

        try:
            self._mcp.run(
                transport=self.config.transport,
                host=self.config.host,
                port=self.config.port,
            )
        except TypeError:
            # 某些版本的 FastMCP run 签名可能不同，做一次保守兜底
            self._mcp.run(self.config.transport)
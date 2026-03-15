from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from ..agent._tool_agent import ToolAgentConfig
from ..envs import StateTransitionRecord, load_backend_from_skill_dir
from ..utils import logger
from ..utils.tool_schema import (
    ToolParameterMapping,
    build_parameter_name_mappings,
    restore_original_argument_names,
)

from .config import MCPRuntimeConfig
from .executors import LLMToolExecutor, ProgramToolExecutor
from .tool_registry import ToolRegistry


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
        skill_dir: Path,
        tools_path: Path,
        state_key: str,
    ):
        self.config = config
        self.skill_dir = skill_dir.resolve()
        self.tools_path = tools_path.resolve()
        self.state_key = state_key

        self.registry = ToolRegistry()
        self.tools = self.registry.load_tools_from_jsonl(self.tools_path)
        self.tool_parameter_mappings = self.build_tool_parameter_mappings()
        self.state_transitions: list[StateTransitionRecord] = []

        has_program_backend = load_backend_from_skill_dir(self.skill_dir) is not None
        if has_program_backend:
            self.executor = ProgramToolExecutor(skill_dir=self.skill_dir)
            self.environment_profile = self.executor.profile.raw
            self.scenario_id = self.executor.scenario_id
        else:
            self.executor = LLMToolExecutor(tool_agent_config=tool_agent_config)
            self.environment_profile = None
            self.scenario_id = None

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

    def build_tool_parameter_mappings(self) -> dict[str, list[ToolParameterMapping]]:
        mappings: dict[str, list[ToolParameterMapping]] = {}
        for schema in self.tools:
            tool_name = schema.get("name")
            if not isinstance(tool_name, str) or not tool_name:
                continue
            tool_params, required_names = self.registry.extract_schema_info(schema)
            mappings[tool_name] = build_parameter_name_mappings(
                tool_params=tool_params,
                required_names=required_names,
            )
        return mappings

    def normalize_tool_arguments(self, *, tool_name: str, arguments: Any) -> Any:
        parameter_mappings = self.tool_parameter_mappings.get(tool_name) or []
        if not parameter_mappings:
            return arguments

        if isinstance(arguments, dict):
            return restore_original_argument_names(
                arguments=arguments,
                parameter_mappings=parameter_mappings,
            )

        if isinstance(arguments, str):
            text = arguments.strip()
            if not text:
                return arguments
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return arguments
            if not isinstance(parsed, dict):
                return arguments
            normalized = restore_original_argument_names(
                arguments=parsed,
                parameter_mappings=parameter_mappings,
            )
            return json.dumps(normalized, ensure_ascii=False)

        return arguments

    def normalize_message_tool_arguments(self, message: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(message)

        function_call = normalized.get("function_call")
        if isinstance(function_call, dict) and function_call.get("name"):
            normalized_function_call = dict(function_call)
            normalized_function_call["arguments"] = self.normalize_tool_arguments(
                tool_name=str(normalized_function_call.get("name", "")),
                arguments=normalized_function_call.get("arguments", {}),
            )
            normalized["function_call"] = normalized_function_call

        raw_tool_calls = normalized.get("tool_calls")
        if isinstance(raw_tool_calls, list):
            normalized_tool_calls: list[Any] = []
            for item in raw_tool_calls:
                if not isinstance(item, dict) or not item.get("name"):
                    normalized_tool_calls.append(item)
                    continue
                normalized_item = dict(item)
                normalized_item["arguments"] = self.normalize_tool_arguments(
                    tool_name=str(normalized_item.get("name", "")),
                    arguments=normalized_item.get("arguments", {}),
                )
                normalized_tool_calls.append(normalized_item)
            normalized["tool_calls"] = normalized_tool_calls

        return normalized

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
        self.registry.create_mcp_tools(
            mcp=self._mcp,
            tools=self.tools,
            handler_factory=self.make_tool_handler,
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
        self.state_transitions.clear()
        self.executor.reset_state(target_key)

    def get_state(self, key: str | None = None) -> dict[str, Any]:
        """
        获取某个 state 分区。
        """
        target_key = key or self.state_key
        return self.executor.get_state(target_key)

    def make_tool_handler(self, schema: dict[str, Any]) -> Any:
        from fastmcp.tools import tool

        name = schema.get("name")
        if not name:
            return None

        description = schema.get("description", "")
        tool_params, required_names = self.registry.extract_schema_info(schema)
        parameter_mappings = self.tool_parameter_mappings.get(name) or build_parameter_name_mappings(
            tool_params=tool_params,
            required_names=required_names,
        )

        @tool(name=name, description=description)
        def _handler(**kwargs: Any) -> str:
            runtime_state_key, runtime_kwargs = self.extract_runtime_state_key(
                kwargs=kwargs,
                default_state_key=self.state_key,
            )
            runtime_kwargs = restore_original_argument_names(
                arguments=runtime_kwargs,
                parameter_mappings=parameter_mappings,
            )
            missing_names = self.registry.find_missing_required_arguments(
                arguments=runtime_kwargs,
                required_names=required_names,
            )
            if missing_names:
                return json.dumps(
                    {
                        "error": {
                            "type": "validation_error",
                            "message": f"Missing required arguments: {', '.join(missing_names)}",
                            "missing": missing_names,
                        }
                    },
                    ensure_ascii=False,
                )
            execution = self.executor.execute_tool(
                tool_name=name,
                arguments=runtime_kwargs,
                state_key=runtime_state_key,
                tool_schema=schema,
                available_tools=self.tools,
            )
            self.state_transitions.append(
                StateTransitionRecord(
                    tool_name=name,
                    arguments=runtime_kwargs,
                    before_state=execution.before_state,
                    after_state=execution.after_state,
                    result=execution.result,
                )
            )
            return execution.response_text

        self.registry.apply_explicit_signature(
            handler=_handler,
            parameter_mappings=parameter_mappings,
            strict_required=False,
        )
        return _handler

    def extract_runtime_state_key(
        self,
        *,
        kwargs: dict[str, Any],
        default_state_key: str,
    ) -> tuple[str, dict[str, Any]]:
        if not isinstance(kwargs, dict):
            return default_state_key, {}

        runtime_key = kwargs.get("__state_key")
        clean_kwargs = {k: v for k, v in kwargs.items() if k != "__state_key"}

        if isinstance(runtime_key, str) and runtime_key.strip():
            return runtime_key.strip(), clean_kwargs

        return default_state_key, clean_kwargs

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

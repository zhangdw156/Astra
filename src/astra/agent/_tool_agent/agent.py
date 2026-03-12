from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from ...utils import config as astra_config
from ...utils import logger

from .config import ToolAgentConfig
from .types import ToolExecutionResult


class ToolAgent:
    """
    ToolAgent：负责生成工具回复与更新状态，并可将 tools.jsonl 注册为轻量 MCP 工具。

    职责：
    1. 读取并缓存 tool-agent prompt 模板
    2. 根据 tool_name / arguments / current_state 构造 prompt
    3. 调用模型生成 <RESPONSE> 与 <STATE>
    4. 解析模型输出为结构化结果
    5. 解析 tools.jsonl
    6. 基于 tools.jsonl 为 FastMCP 注册通用 handler
    """

    _DEFAULT_STATE_KEY = "default"

    def __init__(self, config: ToolAgentConfig):
        self.config = config.normalized()
        self.prompt_text = self.config.prompt_path.read_text(encoding="utf-8")
        self._state_store: dict[str, dict[str, Any]] = {}

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def generate_response(
        self,
        *,
        tool_name: str,
        arguments_json: str,
        session_state: dict[str, Any] | None = None,
        conversation_context: str | None = None,
        tool_schema: dict[str, Any] | None = None,
        available_tools: list[dict[str, Any]] | None = None,
    ) -> ToolExecutionResult:
        """
        调用大模型生成工具回复与新状态。
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        prompt = self.build_prompt(
            tool_name=tool_name,
            arguments_json=arguments_json,
            tool_schema=tool_schema,
            available_tools=available_tools,
            current_state=session_state,
            conversation_context=conversation_context,
        )

        content = self.call_model(prompt)
        response_text, new_state = self.parse_response(content)

        return ToolExecutionResult(
            response=response_text,
            state=new_state,
        )

    def load_tools_from_jsonl(self, tools_jsonl: Path) -> list[dict[str, Any]]:
        """
        解析 tools.jsonl。

        每行一个 JSON 对象，需包含 "name" 字段；无效行跳过并打印警告。
        """
        tools: list[dict[str, Any]] = []
        if not tools_jsonl.exists():
            return tools

        for line in tools_jsonl.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in tools.jsonl line: {}", stripped[:120])
                continue

            if isinstance(obj, dict) and "name" in obj:
                tools.append(obj)

        return tools

    def create_mcp_tools(
        self,
        *,
        mcp: Any,
        tools: list[dict[str, Any]],
        state_key: str = _DEFAULT_STATE_KEY,
    ) -> None:
        """
        基于 tools 列表向 FastMCP 实例注册通用 LLM 工具 handler。
        """
        from fastmcp import FastMCP

        if not isinstance(mcp, FastMCP):
            raise TypeError("mcp 须为 FastMCP 实例")

        for schema in tools:
            name = schema.get("name")
            if not name:
                continue

            description = schema.get("description", "")
            tool_params, required_names = self.extract_schema_info(schema)

            handler = self.make_tool_handler(
                tool_name=name,
                tool_description=description,
                tool_params=tool_params,
                required_names=required_names,
                tool_schema=schema,
                available_tools=tools,
                state_key=state_key,
            )
            mcp.add_tool(handler)

    # -------------------------------------------------------------------------
    # Prompt / LLM / Parsing
    # -------------------------------------------------------------------------

    def build_prompt(
        self,
        *,
        tool_name: str,
        arguments_json: str,
        tool_schema: dict[str, Any] | None = None,
        available_tools: list[dict[str, Any]] | None = None,
        current_state: dict[str, Any] | None = None,
        conversation_context: str | None = None,
    ) -> str:
        """
        根据模板与上下文构造提示词。
        """
        text = self.prompt_text.replace("{TOOL_NAME}", tool_name)
        text = text.replace("{TOOL_ARGUMENTS}", arguments_json or "{}")
        text = text.replace(
            "{TOOL_SCHEMA}",
            json.dumps(tool_schema or {}, ensure_ascii=False, indent=2),
        )
        text = text.replace(
            "{AVAILABLE_TOOLS}",
            json.dumps(available_tools or [], ensure_ascii=False, indent=2),
        )
        text = text.replace(
            "{CURRENT_STATE}",
            json.dumps(current_state or {}, ensure_ascii=False, indent=2),
        )
        text = text.replace(
            "{CONVERSATION_CONTEXT}",
            (conversation_context or "").strip() or "(empty)",
        )
        return text

    def call_model(self, prompt: str) -> str:
        """
        调用模型生成 tool response 原始文本。
        """
        api_key = astra_config.get_tool_agent_api_key()
        model = astra_config.get_tool_agent_model()
        base_url = astra_config.get_tool_agent_base_url()

        logger.info("Calling tool model: {}", model)
        logger.debug("Tool prompt length: {} chars", len(prompt))

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        content = (response.choices[0].message.content or "").strip()
        logger.debug("Tool raw response length: {} chars", len(content))
        return content

    def parse_response(self, text: str) -> tuple[str, dict[str, Any]]:
        """
        解析模型输出中的 <RESPONSE> 与 <STATE> 块。
        返回 (response_json_str, new_state_dict)。
        """
        response_match = re.search(
            r"<RESPONSE>\s*([\s\S]*?)\s*</RESPONSE>",
            text,
            flags=re.IGNORECASE,
        )
        raw_response = (
            response_match.group(1).strip() if response_match else text.strip()
        ) or ""

        response_str: str
        try:
            parsed = json.loads(raw_response)
            response_str = json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    parsed = json.loads(raw_response[start:end])
                    response_str = json.dumps(parsed, ensure_ascii=False)
                except json.JSONDecodeError:
                    response_str = json.dumps(
                        {"raw": raw_response[:2000], "parse_error": True},
                        ensure_ascii=False,
                    )
            else:
                response_str = json.dumps(
                    {"raw": raw_response[:2000], "parse_error": True},
                    ensure_ascii=False,
                )

        state_match = re.search(
            r"<STATE>\s*([\s\S]*?)\s*</STATE>",
            text,
            flags=re.IGNORECASE,
        )
        state_obj: dict[str, Any] = {}
        if state_match:
            raw_state = state_match.group(1).strip()
            try:
                parsed = json.loads(raw_state or "{}")
                if isinstance(parsed, dict):
                    state_obj = parsed
            except json.JSONDecodeError:
                state_obj = {}

        return response_str, state_obj

    # -------------------------------------------------------------------------
    # State Store
    # -------------------------------------------------------------------------

    def get_state(self, key: str = _DEFAULT_STATE_KEY) -> dict[str, Any]:
        """
        获取当前会话状态。
        """
        return self._state_store.get(key, {})

    def set_state(self, state: dict[str, Any], key: str = _DEFAULT_STATE_KEY) -> None:
        """
        写回当前会话状态。
        """
        self._state_store[key] = state or {}

    # -------------------------------------------------------------------------
    # MCP Tool Registration Helpers
    # -------------------------------------------------------------------------

    def extract_runtime_state_key(
        self,
        *,
        kwargs: dict[str, Any],
        default_state_key: str,
    ) -> tuple[str, dict[str, Any]]:
        """
        允许调用方通过保留参数 __state_key 指定本次调用的状态分区。
        返回 (state_key, clean_kwargs)。
        """
        if not isinstance(kwargs, dict):
            return default_state_key, {}

        runtime_key = kwargs.get("__state_key")
        clean_kwargs = {k: v for k, v in kwargs.items() if k != "__state_key"}

        if isinstance(runtime_key, str) and runtime_key.strip():
            return runtime_key.strip(), clean_kwargs

        return default_state_key, clean_kwargs

    def extract_schema_info(
        self,
        schema: dict[str, Any],
    ) -> tuple[dict[str, Any], set[str]]:
        """
        从 inputSchema 中提取参数定义与 required 参数名集合。
        """
        input_schema = schema.get("inputSchema", {})
        if not isinstance(input_schema, dict):
            return {}, set()

        properties = input_schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        required = input_schema.get("required", [])
        required_names = {x for x in required if isinstance(x, str)}

        return properties, required_names

    def schema_type_to_pytype(self, schema_type: Any) -> Any:
        """
        将 JSON Schema 基础类型映射到 Python 注解类型。
        """
        if schema_type == "integer":
            return int
        if schema_type == "number":
            return float
        if schema_type == "boolean":
            return bool
        if schema_type == "array":
            return list
        if schema_type == "object":
            return dict
        return str

    def apply_explicit_signature(
        self,
        *,
        handler: Any,
        tool_params: dict[str, Any],
        required_names: set[str],
        allow_state_key: bool = True,
    ) -> None:
        """
        给 handler 注入显式签名，避免 FastMCP 因 **kwargs 拒绝注册。
        同时保留 __state_key 入口。

        规则：
        - required 参数使用 inspect.Parameter.empty，表现为真正必填
        - 非 required 参数若 schema 提供 default，则使用该默认值
        - 否则默认值为 None
        """
        parameters: list[inspect.Parameter] = []
        annotations: dict[str, Any] = {}

        for name, info in tool_params.items():
            if not isinstance(name, str):
                continue
            if not name.isidentifier() or name == "__state_key":
                continue

            schema_type = info.get("type", "string") if isinstance(info, dict) else "string"
            pytype = self.schema_type_to_pytype(schema_type)

            if name in required_names:
                default = inspect.Parameter.empty
            elif isinstance(info, dict) and "default" in info:
                default = info.get("default")
            else:
                default = None

            parameters.append(
                inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=pytype,
                )
            )
            annotations[name] = pytype

        if allow_state_key and "__state_key" not in tool_params:
            parameters.append(
                inspect.Parameter(
                    name="__state_key",
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default="",
                    annotation=str,
                )
            )
            annotations["__state_key"] = str

        handler.__signature__ = inspect.Signature(
            parameters=parameters,
            return_annotation=str,
        )
        handler.__annotations__ = {**annotations, "return": str}

    def make_tool_handler(
        self,
        *,
        tool_name: str,
        tool_description: str,
        tool_params: dict[str, Any],
        required_names: set[str],
        tool_schema: dict[str, Any],
        available_tools: list[dict[str, Any]],
        state_key: str,
    ) -> Any:
        """
        工厂函数：为每个工具创建可注册到 FastMCP 的处理函数。
        """
        from fastmcp.tools import tool

        @tool(name=tool_name, description=tool_description)
        def _handler(**kwargs: Any) -> str:
            runtime_state_key, runtime_kwargs = self.extract_runtime_state_key(
                kwargs=kwargs,
                default_state_key=state_key,
            )
            current_state = self.get_state(runtime_state_key)
            arguments_json = json.dumps(runtime_kwargs, ensure_ascii=False)

            result = self.generate_response(
                tool_name=tool_name,
                arguments_json=arguments_json,
                session_state=current_state,
                conversation_context=None,
                tool_schema=tool_schema,
                available_tools=available_tools,
            )

            if isinstance(result.state, dict):
                self.set_state(result.state, runtime_state_key)

            response = (result.response or "").strip()
            if not response:
                response = json.dumps(
                    {"status": "executed", "tool": tool_name},
                    ensure_ascii=False,
                )

            return response

        self.apply_explicit_signature(
            handler=_handler,
            tool_params=tool_params,
            required_names=required_names,
        )
        return _handler
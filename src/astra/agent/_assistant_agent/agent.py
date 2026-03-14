from __future__ import annotations

from typing import Any

from ...utils import config as astra_config
from ...utils import logger

from .config import AssistantAgentConfig
from .types import AssistantToolCall, AssistantTurnResult


class AssistantAgent:
    """
    AssistantAgent：封装 qwen-agent Assistant + MCP tools，提供 turn-level 运行能力。

    职责：
    1. 构造 assistant 的 llm 配置
    2. 构造 MCP 配置
    3. 应用 qwen-agent 相关 patch
    4. 创建底层 Assistant
    5. 执行单轮 assistant run
    6. 规范化返回消息
    """

    def __init__(self, config: AssistantAgentConfig):
        self.config = config
        self._agent = None

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def create(self, *, state_key: str = "") -> None:
        """
        创建底层 qwen-agent Assistant，并加载 MCP tools。
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        if self.config.enable_json_patch:
            self.patch_nous_fncall_json_parsing()

        if self.config.enable_mcp_patch:
            self.patch_mcp_tool_params(state_key=state_key)

        from qwen_agent.agents import Assistant

        llm_cfg = self.build_llm_config()
        mcp_cfg = self.build_mcp_config()

        self._agent = Assistant(
            llm=llm_cfg,
            system_message=self.config.system_message.strip(),
            function_list=[mcp_cfg],
        )

        logger.info("Assistant agent created with MCP url: {}", self.config.mcp_url)

    def get_tool_names(self) -> list[str]:
        """
        返回当前 Assistant 已加载的工具名列表。
        """
        if self._agent is None:
            return []
        return list(self._agent.function_map.keys())

    def run_turn(self, *, messages: list[dict[str, Any]]) -> AssistantTurnResult:
        """
        执行一轮 assistant 推理与工具调用。
        """
        if self._agent is None:
            raise RuntimeError("Assistant 尚未创建，请先调用 create()")

        last_response: list[Any] = []
        for response in self._agent.run(messages=messages):
            last_response = response if isinstance(response, list) else [response]

        normalized_messages: list[dict[str, Any]] = []
        for msg in last_response:
            item = self.message_to_dict(msg)
            if item:
                normalized_messages.append(item)

        assistant_message = ""
        tool_calls: list[AssistantToolCall] = []

        for message in normalized_messages:
            role = message.get("role", "")

            if role == "assistant":
                content = (message.get("content") or "").strip()
                if content:
                    assistant_message = content

                function_call = message.get("function_call") or {}
                if isinstance(function_call, dict) and function_call.get("name"):
                    tool_calls.append(
                        AssistantToolCall(
                            name=function_call.get("name", ""),
                            arguments=function_call.get("arguments", "{}"),
                            result="",
                        )
                    )

            elif role == "function":
                function_name = message.get("name", "")
                function_result = message.get("content", "") or ""

                # 按顺序匹配最早一个同名且尚未填充 result 的调用
                for call in tool_calls:
                    if call.name == function_name and not call.result:
                        call.result = function_result
                        break

        return AssistantTurnResult(
            messages=normalized_messages,
            assistant_message=assistant_message,
            tool_calls=tool_calls,
            raw_response=last_response,
        )

    def get_agent_system_prompt(self) -> str:
        """
        获取 qwen-agent 实际看到的完整系统提示词。
        """
        if self._agent is None:
            return ""

        from qwen_agent.llm.schema import SYSTEM, ContentItem, Message

        system_message = getattr(self._agent, "system_message", "") or ""
        functions = [func.function for func in self._agent.function_map.values()]
        messages = [Message(role=SYSTEM, content=[ContentItem(text=system_message)])]
        generate_cfg = {"parallel_function_calls": True, "function_choice": "auto"}

        if functions and hasattr(self._agent.llm, "_preprocess_messages"):
            messages = self._agent.llm._preprocess_messages(
                messages=messages,
                lang="en",
                generate_cfg=generate_cfg,
                functions=functions,
            )

        if not messages or messages[0].role != SYSTEM:
            return system_message

        return self.content_to_text(messages[0].content)

    # -------------------------------------------------------------------------
    # Qwen / MCP Config
    # -------------------------------------------------------------------------

    def build_llm_config(self) -> dict[str, Any]:
        """
        根据 astra_config 构建 Assistant Agent 的 LLM 配置（OpenAI 兼容）。
        """
        api_key = astra_config.get_assistant_agent_api_key()
        model = astra_config.get_assistant_agent_model()
        base_url = astra_config.get_assistant_agent_base_url()

        return {
            "model": model,
            "model_type": "oai",
            "model_server": base_url or "https://api.openai.com/v1",
            "api_key": api_key,
        }

    def build_mcp_config(self) -> dict[str, Any]:
        """
        构建 MCP 配置。
        """
        return {
            "mcpServers": {
                "skill-tools": {
                    "url": self.config.mcp_url,
                    "timeout": 30000,
                }
            }
        }

    # -------------------------------------------------------------------------
    # Message Normalization
    # -------------------------------------------------------------------------

    def content_to_text(self, content: Any) -> str:
        """
        从 Message.content（str 或 List[ContentItem]）提取纯文本。
        """
        if isinstance(content, str):
            return content or ""
        if isinstance(content, list):
            return "".join((getattr(item, "text", None) or "") for item in content)
        return ""

    def extract_reasoning(self, content: str) -> tuple[str, str]:
        """
        从 assistant content 中提取 <think>...</think>。
        返回 (reasoning, clean_content)。
        """
        import re

        text = content or ""
        reasoning_parts: list[str] = []
        pattern = r"<think>(.*?)</think>"

        for match in re.finditer(pattern, text, re.DOTALL):
            reasoning_parts.append(match.group(1).strip())

        if reasoning_parts:
            reasoning = "\n\n".join(reasoning_parts)
            clean_content = re.sub(pattern, "", text, flags=re.DOTALL).strip()
            return reasoning, clean_content

        return "", text

    def message_to_dict(self, msg: Any) -> dict[str, Any] | None:
        """
        将 qwen-agent Message 转为可序列化的 dict，并剥离 reasoning_content。
        """
        if isinstance(msg, dict):
            data = dict(msg)
        else:
            data = getattr(msg, "__dict__", {}) or {}
            if hasattr(msg, "get"):
                data = dict(msg)

        role = data.get("role")
        if not role:
            return None

        raw_content = data.get("content", "") or ""
        output: dict[str, Any] = {"role": role, "content": raw_content}

        if role == "assistant" and raw_content:
            _, clean_content = self.extract_reasoning(raw_content)
            output["content"] = clean_content

        if "function_call" in data and data["function_call"]:
            output["function_call"] = data["function_call"]

        if "name" in data and data["name"]:
            output["name"] = data["name"]

        return output

    # -------------------------------------------------------------------------
    # Compatibility Patches
    # -------------------------------------------------------------------------

    def patch_mcp_tool_params(self, *, state_key: str = "") -> None:
        """
        对 qwen_agent MCP 工具的 call 做容错，并注入 __state_key。
        """
        try:
            import json as _json
            import re as _re
            from qwen_agent.tools import mcp_manager

            original_create = mcp_manager.MCPManager.create_tool_class

            def normalize_tool_params(params) -> dict:
                def unwrap_mapping(candidate):
                    if not isinstance(candidate, dict):
                        return None

                    arguments = candidate.get("arguments")
                    if isinstance(arguments, dict):
                        return arguments
                    if isinstance(arguments, str):
                        nested = parse_text_to_dict(arguments)
                        if nested is not None:
                            return nested
                    return candidate

                def parse_text_to_dict(text: str) -> dict | None:
                    value = (text or "").strip()
                    if not value:
                        return {}

                    candidates = [value]

                    fenced = _re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", value)
                    if fenced:
                        candidates.insert(0, fenced.group(1).strip())

                    args_idx = value.find('"arguments"')
                    if args_idx >= 0:
                        candidates.append(value[args_idx:])

                    brace_starts = [m.start() for m in _re.finditer(r"\{", value)]
                    for start in brace_starts:
                        candidates.append(value[start:])

                    seen: set[str] = set()
                    decoder = _json.JSONDecoder()
                    for candidate in candidates:
                        candidate = candidate.strip()
                        if not candidate or candidate in seen:
                            continue
                        seen.add(candidate)

                        for attempt in (
                            candidate,
                            candidate.rstrip(","),
                            candidate + "}",
                            candidate.rstrip(",") + "}",
                        ):
                            try:
                                parsed, _ = decoder.raw_decode(attempt)
                            except _json.JSONDecodeError:
                                pass
                            else:
                                normalized = unwrap_mapping(parsed)
                                if normalized is not None:
                                    return normalized

                            try:
                                import json5

                                parsed = json5.loads(attempt)
                            except Exception:
                                continue
                            normalized = unwrap_mapping(parsed)
                            if normalized is not None:
                                return normalized

                    # Last resort: recover simple JSON-style key/value pairs from fragments.
                    recovered: dict[str, object] = {}
                    string_pairs = _re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*"([^"]*)"', value)
                    number_pairs = _re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*(-?\d+(?:\.\d+)?)', value)
                    bool_pairs = _re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*(true|false|null)', value, flags=_re.IGNORECASE)

                    for key, raw in string_pairs:
                        recovered[key] = raw
                    for key, raw in number_pairs:
                        recovered.setdefault(key, float(raw) if "." in raw else int(raw))
                    for key, raw in bool_pairs:
                        lowered = raw.lower()
                        recovered.setdefault(
                            key,
                            True if lowered == "true" else False if lowered == "false" else None,
                        )

                    return recovered or None

                if params is None:
                    return {}
                if isinstance(params, dict):
                    normalized = unwrap_mapping(params)
                    return normalized or {}

                value = params if isinstance(params, str) else str(params)
                normalized = parse_text_to_dict(value)
                return normalized or {}

            def patched_create_tool_class(
                manager_self,
                register_name,
                register_client_id,
                tool_name,
                tool_desc,
                tool_parameters,
            ):
                tool_instance = original_create(
                    manager_self,
                    register_name,
                    register_client_id,
                    tool_name,
                    tool_desc,
                    tool_parameters,
                )
                original_call = tool_instance.call

                def patched_call(params, **kwargs):
                    tool_args = normalize_tool_params(params)
                    if state_key:
                        tool_args["__state_key"] = state_key
                    return original_call(_json.dumps(tool_args), **kwargs)

                tool_instance.call = patched_call
                return tool_instance

            mcp_manager.MCPManager.create_tool_class = patched_create_tool_class

        except Exception as exc:
            import warnings
            warnings.warn(f"MCP params 容错 patch 未生效: {exc}", RuntimeWarning)

    def patch_nous_fncall_json_parsing(self) -> None:
        """
        给 qwen-agent 的 NousFnCallPrompt 增加更宽松的 JSON 解析。
        """
        try:
            import json as _json
            from qwen_agent.llm.fncall_prompts import nous_fncall_prompt as _nfp

            original_json5_loads = _nfp.json5.loads

            def loads_with_recovery(payload, *args, **kwargs):
                if isinstance(payload, str):
                    text = payload.strip()
                    if not text:
                        return {}

                    candidates = [text]
                    if len(text) <= 2000:
                        candidates.extend([text + "}", text.rstrip(",") + "}"])

                    for candidate in candidates:
                        try:
                            parsed = original_json5_loads(candidate, *args, **kwargs)
                            if isinstance(parsed, str):
                                inner = parsed.strip()
                                if inner.startswith("{") or inner.startswith("["):
                                    try:
                                        return original_json5_loads(inner, *args, **kwargs)
                                    except Exception:
                                        try:
                                            return _json.loads(inner)
                                        except Exception:
                                            pass
                            return parsed
                        except Exception:
                            try:
                                parsed = _json.loads(candidate)
                                if isinstance(parsed, str):
                                    inner = parsed.strip()
                                    if inner.startswith("{") or inner.startswith("["):
                                        return _json.loads(inner)
                                return parsed
                            except Exception:
                                pass

                return original_json5_loads(payload, *args, **kwargs)

            _nfp.json5.loads = loads_with_recovery

        except Exception as exc:
            import warnings
            warnings.warn(f"NousFnCallPrompt JSON 容错 patch 未生效: {exc}", RuntimeWarning)

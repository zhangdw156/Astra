from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Callable

from ..utils import logger
from ..utils.tool_schema import ToolParameterMapping


class ToolRegistry:
    def load_tools_from_jsonl(self, tools_jsonl: Path) -> list[dict[str, Any]]:
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
        handler_factory: Callable[[dict[str, Any]], Any],
    ) -> None:
        from fastmcp import FastMCP

        if not isinstance(mcp, FastMCP):
            raise TypeError("mcp 须为 FastMCP 实例")

        for schema in tools:
            handler = handler_factory(schema)
            if handler is not None:
                mcp.add_tool(handler)

    def extract_schema_info(
        self,
        schema: dict[str, Any],
    ) -> tuple[dict[str, Any], set[str]]:
        input_schema = schema.get("inputSchema", {})
        if not isinstance(input_schema, dict):
            return {}, set()

        properties = input_schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}

        required = input_schema.get("required", [])
        required_names = {x for x in required if isinstance(x, str)}
        return properties, required_names

    def apply_explicit_signature(
        self,
        *,
        handler: Any,
        parameter_mappings: list[ToolParameterMapping],
        allow_state_key: bool = True,
        strict_required: bool = True,
    ) -> None:
        parameters: list[inspect.Parameter] = []
        annotations: dict[str, Any] = {}

        for mapping in parameter_mappings:
            name = mapping.public_name
            info = mapping.schema
            schema_type = info.get("type", "string") if isinstance(info, dict) else "string"
            pytype = self.schema_type_to_pytype(schema_type)

            if mapping.required and strict_required:
                default = inspect.Parameter.empty
                annotation = pytype
            elif isinstance(info, dict) and "default" in info:
                default = info.get("default")
                annotation = pytype
            else:
                default = None
                annotation = pytype | None

            parameters.append(
                inspect.Parameter(
                    name=name,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=default,
                    annotation=annotation,
                )
            )
            annotations[name] = annotation

        has_explicit_state_key = any(
            mapping.original_name == "__state_key" for mapping in parameter_mappings
        )
        if allow_state_key and not has_explicit_state_key:
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

    def find_missing_required_arguments(
        self,
        *,
        arguments: dict[str, Any],
        required_names: set[str],
    ) -> list[str]:
        missing: list[str] = []
        for name in required_names:
            if name not in arguments:
                missing.append(name)
                continue
            value = arguments[name]
            if value is None:
                missing.append(name)
                continue
            if isinstance(value, str) and not value.strip():
                missing.append(name)
        return missing

    def schema_type_to_pytype(self, schema_type: Any) -> Any:
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

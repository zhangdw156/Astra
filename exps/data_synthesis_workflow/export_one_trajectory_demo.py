#!/usr/bin/env python3
"""将单条 trajectory 导出为 Qwen3 工具调用 SFT 格式的 JSON。

使用方法
--------
    uv run exps/data_synthesis_workflow/export_one_trajectory_demo.py \
        --trajectory <输入 trajectory.json> \
        --output <输出 JSON 路径>

参数
----
--trajectory (必需)
    输入的 trajectory.json 文件路径。
--output (必需)
    输出的 Qwen3 SFT JSON 文件路径；若目录不存在会自动创建。

使用示例
--------
    uv run exps/data_synthesis_workflow/export_one_trajectory_demo.py \
        --trajectory artifacts/pipeline1_results/1822_code-search/8/trajectory.json \
        --output artifacts/pipeline1_results/1822_code-search/8/qwen3_sft_output.json
"""
from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


TOOL_PREFIX = "skill-tools-"
RUNTIME_ARGUMENT_KEYS = {"__state_key"}
SYSTEM_PROMPT = (
    "You are an expert in composing functions. You are given a question and a set of "
    "possible functions. Based on the\nquestion, you will need to make one or more "
    "function/tool calls to achieve the purpose.\nIf none of the functions can be used, "
    "point it out. If the given question lacks the parameters required by the\nfunction, "
    "also point it out.\nYou should only return the function calls in your response.\n\n"
    "If you decide to invoke any of the function(s), you MUST put it in the format of "
    "<tool_call>...</tool_call>\nYou SHOULD NOT include any other text in the response.\n\n"
    "At each turn, you should try your best to complete the tasks requested by the user "
    "within the current turn.\nContinue to output functions to call until you have "
    "fulfilled the user's request to the best of your ability. Once\nyou have no more "
    "functions to call, the system will consider the current turn complete and proceed "
    "to the next turn\nor task."
)
QWEN3_SYSTEM_TEMPLATE = """{%- if tools %}
    {{- '<|im_start|>system\\n' }}
    {%- if messages[0].role == 'system' %}
        {{- messages[0].content + '\\n\\n' }}
    {%- endif %}
    {{- "# Tools\\n\\nYou may call one or more functions to assist with the user query.\\n\\nYou are provided with function signatures within <tools></tools> XML tags:\\n<tools>" }}
    {%- for tool in tools %}
        {{- "\\n" }}
        {{- tool | tojson }}
    {%- endfor %}
    {{- "\\n</tools>\\n\\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\\n<tool_call>\\n{\\"name\\": <function-name>, \\"arguments\\": <args-json-object>}\\n</tool_call><|im_end|>\\n" }}
{%- else %}
    {%- if messages[0].role == 'system' %}
        {{- '<|im_start|>system\\n' + messages[0].content + '<|im_end|>\\n' }}
    {%- endif %}
{%- endif %}

{# 计算多轮工具调用的状态 #}
{%- set ns = namespace(multi_step_tool=true, last_query_index=messages|length - 1) %}
{%- for message in messages[::-1] %}
    {%- set index = (messages|length - 1) - loop.index0 %}
    {%- if ns.multi_step_tool and message.role == "user" and not(message.content.startswith('<tool_response>') and message.content.endswith('</tool_response>')) %}
        {%- set ns.multi_step_tool = false %}
        {%- set ns.last_query_index = index %}
    {%- endif %}
{%- endfor %}

{%- for message in messages %}
    {%- if (message.role == "user") or (message.role == "system" and not loop.first) %}
        {{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>' + '\\n' }}

    {%- elif message.role == "assistant" %}
        {%- set content = message.content %}
        {%- set reasoning_content = '' %}

        {%- if message.reasoning_content is defined and message.reasoning_content is not none %}
            {%- set reasoning_content = message.reasoning_content %}
        {%- else %}
            {%- if '</think>' in message.content %}
                {%- set content = message.content.split('</think>')[-1].lstrip('\\n') %}
                {%- set reasoning_content = message.content.split('</think>')[0].rstrip('\\n').split('<think>')[-1].lstrip('\\n') %}
            {%- endif %}
        {%- endif %}

        {%- if loop.index0 > ns.last_query_index %}
            {%- if loop.last or (not loop.last and reasoning_content) %}
                {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content.strip('\\n') + '\\n</think>\\n\\n' + content.lstrip('\\n') }}
            {%- else %}
                {{- '<|im_start|>' + message.role + '\\n' + content }}
            {%- endif %}
        {%- else %}
            {{- '<|im_start|>' + message.role + '\\n' + content }}
        {%- endif %}

        {%- if message.tool_calls %}
            {%- for tool_call in message.tool_calls %}
                {%- if (loop.first and content) or (not loop.first) %}
                    {{- '\\n' }}
                {%- endif %}
                {%- if tool_call.function %}
                    {%- set tool_call = tool_call.function %}
                {%- endif %}
                {{- '<tool_call>\\n{\\"name\\": "' }}
                {{- tool_call.name }}
                {{- '", "arguments": ' }}
                {%- if tool_call.arguments is string %}
                    {{- tool_call.arguments }}
                {%- else %}
                    {{- tool_call.arguments | tojson }}
                {%- endif %}
                {{- '}\\n</tool_call>' }}
            {%- endfor %}
        {%- endif %}
        {{- '<|im_end|>\\n' }}

    {%- elif message.role == "tool" %}
        {%- if loop.first or (messages[loop.index0 - 1].role != "tool") %}
            {{- '<|im_start|>user' }}
        {%- endif %}
        {{- '\\n<tool_response>\\n' }}
        {{- message.content }}
        {{- '\\n</tool_response>' }}
        {%- if loop.last or (messages[loop.index0 + 1].role != "tool") %}
            {{- '<|im_end|>\\n' }}
        {%- endif %}
    {%- endif %}
{%- endfor %}

{%- if add_generation_prompt %}
    {{- '<|im_start|>assistant\\n' }}
    {%- if enable_thinking is defined and enable_thinking is false %}
        {{- '<think>\\n\\n</think>\\n\\n' }}
    {%- endif %}
{%- endif %}"""


def strip_tool_prefix(name: Any) -> str:
    text = str(name or "").strip()
    if text.startswith(TOOL_PREFIX):
        return text[len(TOOL_PREFIX) :]
    return text


def try_parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def clean_runtime_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            str(key): clean_runtime_keys(value)
            for key, value in obj.items()
            if str(key) not in RUNTIME_ARGUMENT_KEYS
        }
    if isinstance(obj, list):
        return [clean_runtime_keys(item) for item in obj]
    return obj


def normalize_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(tool)
    normalized["name"] = strip_tool_prefix(normalized.get("name", ""))
    parameters = normalized.pop("inputSchema", None)
    if parameters is None:
        parameters = normalized.get("parameters")
    normalized["parameters"] = clean_runtime_keys(parameters or {"type": "object", "properties": {}})
    return normalized


def normalize_tools(raw_tools: list[Any]) -> list[dict[str, Any]]:
    return [normalize_tool_schema(tool) for tool in raw_tools if isinstance(tool, dict)]


def normalize_function_call_obj(name: Any, arguments: Any) -> dict[str, Any]:
    parsed_arguments = clean_runtime_keys(try_parse_json(arguments))
    if not isinstance(parsed_arguments, dict):
        parsed_arguments = {"_raw": parsed_arguments}
    return {
        "name": strip_tool_prefix(name),
        "arguments": parsed_arguments,
    }


def format_tool_call_block(name: Any, arguments: Any) -> str:
    return "<tool_call>\n" + json.dumps(
        normalize_function_call_obj(name, arguments),
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n</tool_call>"


def format_tool_response_block(content: Any) -> str:
    body = "" if content is None else str(content)
    return f"<tool_response>\n{body}\n</tool_response>"


def extract_tool_call_dicts_from_content(content: Any) -> list[dict[str, Any]]:
    if not isinstance(content, str) or not content.strip():
        return []
    pattern = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)
    calls: list[dict[str, Any]] = []
    for raw_block in pattern.findall(content):
        parsed = try_parse_json(raw_block.strip())
        if not isinstance(parsed, dict):
            continue
        calls.append(
            normalize_function_call_obj(
                parsed.get("name", ""),
                parsed.get("arguments", {}),
            )
        )
    return calls


def extract_message_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls: list[dict[str, Any]] = []

    function_call = message.get("function_call")
    if isinstance(function_call, dict) and function_call.get("name"):
        tool_calls.append(
            normalize_function_call_obj(
                function_call.get("name"),
                function_call.get("arguments", {}),
            )
        )

    raw_tool_calls = message.get("tool_calls")
    if isinstance(raw_tool_calls, list):
        for item in raw_tool_calls:
            if isinstance(item, dict) and isinstance(item.get("function"), dict):
                item = item["function"]
            if isinstance(item, dict) and item.get("name"):
                tool_calls.append(
                    normalize_function_call_obj(
                        item.get("name"),
                        item.get("arguments", {}),
                    )
                )

    tool_calls.extend(extract_tool_call_dicts_from_content(message.get("content")))
    return tool_calls


def build_system_content(tools: list[dict[str, Any]]) -> str:
    tool_lines = "\n".join(json.dumps(tool, ensure_ascii=False) for tool in tools)
    if tools:
        return (
            SYSTEM_PROMPT
            + "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\n"
            + "You are provided with function signatures within <tools></tools> XML tags:\n<tools>"
            + (f"\n{tool_lines}\n" if tool_lines else "\n")
            + "</tools>\n\nFor each function call, return a json object with function name and "
            + "arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n"
            + '{"name": <function-name>, "arguments": <args-json-object>}\n</tool_call>'
        )
    return SYSTEM_PROMPT


def rebuild_messages(raw_messages: list[Any], system_content: str) -> list[dict[str, str]]:
    rebuilt: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    pending_assistant_texts: list[str] = []
    pending_assistant_tool_calls: list[dict[str, Any]] = []
    seen_user = False

    def flush_assistant() -> None:
        nonlocal pending_assistant_texts, pending_assistant_tool_calls
        if pending_assistant_tool_calls:
            content = "\n".join(
                format_tool_call_block(call["name"], call["arguments"])
                for call in pending_assistant_tool_calls
            )
            rebuilt.append({"role": "assistant", "content": content})
        else:
            content = "\n".join(text for text in pending_assistant_texts if text.strip()).strip()
            if content:
                rebuilt.append({"role": "assistant", "content": content})
        pending_assistant_texts = []
        pending_assistant_tool_calls = []

    for raw_message in raw_messages:
        if not isinstance(raw_message, dict):
            continue

        role = str(raw_message.get("role", "")).strip()
        if role == "system":
            continue

        if role == "user":
            flush_assistant()
            rebuilt.append({"role": "user", "content": str(raw_message.get("content", "") or "")})
            seen_user = True
            continue

        if not seen_user:
            continue

        if role == "assistant":
            content = str(raw_message.get("content", "") or "").strip()
            tool_calls = extract_message_tool_calls(raw_message)
            if tool_calls:
                pending_assistant_tool_calls.extend(tool_calls)
            elif content:
                pending_assistant_texts.append(content)
            continue

        if role in {"function", "tool"}:
            flush_assistant()
            rebuilt.append(
                {
                    "role": "user",
                    "content": format_tool_response_block(raw_message.get("content", "")),
                }
            )
            continue

        flush_assistant()
        content = str(raw_message.get("content", "") or "")
        if content:
            rebuilt.append({"role": role, "content": content})

    flush_assistant()
    return rebuilt


def build_output_record(trajectory: dict[str, Any], source_trajectory_path: str) -> dict[str, Any]:
    raw_tools = trajectory.get("tools") or trajectory.get("tools_jsonl") or []
    if not isinstance(raw_tools, list):
        raw_tools = []

    raw_messages = trajectory.get("messages") or []
    if not isinstance(raw_messages, list):
        raise ValueError("trajectory.messages 必须是数组")

    tools = normalize_tools(raw_tools)
    system_content = build_system_content(tools)
    _ = QWEN3_SYSTEM_TEMPLATE

    return {
        "source_trajectory_path": source_trajectory_path,
        "run_id": trajectory.get("run_id", ""),
        "trajectory_id": trajectory.get("trajectory_id", ""),
        "blueprint_id": trajectory.get("blueprint_id", ""),
        "skill_name": trajectory.get("skill_name", ""),
        "persona_id": trajectory.get("persona_id", ""),
        "messages": rebuild_messages(raw_messages, system_content),
        "tools": tools,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export one trajectory into Qwen3 tool-calling SFT JSON.")
    parser.add_argument("--trajectory", type=Path, required=True, help="Input trajectory.json path")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    args = parser.parse_args()

    source_trajectory_path = str(args.trajectory)
    trajectory_path = args.trajectory.resolve()
    output_path = args.output.resolve()

    if not trajectory_path.exists():
        raise FileNotFoundError(f"trajectory 文件不存在: {trajectory_path}")

    trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
    if not isinstance(trajectory, dict):
        raise ValueError("trajectory 文件内容必须是 JSON object")

    output = build_output_record(trajectory, source_trajectory_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

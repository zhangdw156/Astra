from __future__ import annotations

import json
import re
from pathlib import Path


class BlueprintValidator:
    """
    负责：
    1. 从模型回复中提取 JSON
    2. 从 tools.jsonl 中解析合法工具名
    3. 校验 blueprint 基本结构
    """

    REQUIRED_FIELDS = [
        "initial_state",
        "user_agent_config",
        "end_condition",
    ]

    ALLOWED_FIELDS = {
        "steps",
        "goals",
        "possible_tool_calls",
        "initial_state",
        "expected_final_state",
        "user_agent_config",
        "end_condition",
    }

    USER_AGENT_CONFIG_KEYS = ("role", "personality", "knowledge_boundary")

    @staticmethod
    def _decode_first_json_object(text: str) -> dict:
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", text):
            try:
                parsed, _ = decoder.raw_decode(text[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        raise json.JSONDecodeError("No JSON object found", text, 0)

    @staticmethod
    def _normalize_tool_groups(
        tool_groups: object,
        *,
        allowed_tool_names: set[str] | None = None,
    ) -> list[list[str]] | None:
        if not isinstance(tool_groups, list):
            return None

        normalized_groups: list[list[str]] = []
        for inner in tool_groups:
            if not isinstance(inner, list):
                continue

            tools: list[str] = []
            for name in inner:
                if not isinstance(name, str):
                    continue
                stripped = name.strip()
                if not stripped:
                    continue
                if allowed_tool_names is not None and stripped not in allowed_tool_names:
                    continue
                if stripped not in tools:
                    tools.append(stripped)
            normalized_groups.append(tools)

        return normalized_groups

    @classmethod
    def normalize(
        cls,
        data: dict,
        allowed_tool_names: set[str] | None = None,
    ) -> dict:
        """
        对 blueprint 做保守归一化，尽量修复常见的轻微结构偏差。

        当前规则：
        1. 新 schema `steps` 与旧 schema `goals`/`possible_tool_calls` 互相补齐
        2. `goal` / `goals` 只保留非空字符串
        3. `possible_tool_calls` 只保留数组项，去掉空/非法工具名，并按 goals 长度截断或补齐
        4. `user_agent_config` 缺失时保留原值，由 validate 继续报错
        """
        normalized = dict(data)

        steps = normalized.get("steps")
        normalized_steps: list[dict] | None = None
        if isinstance(steps, list):
            normalized_steps = []
            for step in steps:
                if not isinstance(step, dict):
                    continue

                goal = step.get("goal")
                if not isinstance(goal, str) or not goal.strip():
                    continue

                tool_groups = cls._normalize_tool_groups(
                    [step.get("possible_tool_calls", [])],
                    allowed_tool_names=allowed_tool_names,
                )
                tools = tool_groups[0] if tool_groups else []
                normalized_steps.append(
                    {
                        "goal": goal.strip(),
                        "possible_tool_calls": tools,
                    }
                )

        if normalized_steps is None:
            goals = normalized.get("goals")
            normalized_goals: list[str] = []
            if isinstance(goals, list):
                normalized_goals = [
                    item.strip()
                    for item in goals
                    if isinstance(item, str) and item.strip()
                ]

            normalized_ptc = cls._normalize_tool_groups(
                normalized.get("possible_tool_calls"),
                allowed_tool_names=allowed_tool_names,
            )
            if normalized_ptc is None:
                normalized_ptc = []

            goal_count = len(normalized_goals)
            if goal_count > 0:
                normalized_ptc = normalized_ptc[:goal_count]
                while len(normalized_ptc) < goal_count:
                    normalized_ptc.append([])

            normalized_steps = [
                {
                    "goal": goal,
                    "possible_tool_calls": normalized_ptc[i] if i < len(normalized_ptc) else [],
                }
                for i, goal in enumerate(normalized_goals)
            ]

        normalized["steps"] = normalized_steps
        normalized["goals"] = [step["goal"] for step in normalized_steps]
        normalized["possible_tool_calls"] = [
            step["possible_tool_calls"] for step in normalized_steps
        ]

        return normalized

    @staticmethod
    def extract_json_from_response(text: str) -> dict:
        """
        从模型回复中提取 JSON。

        允许以下情况：
        1. ```json ... ```
        2. ``` ... ```
        3. 前后带说明文字，只取第一个 { 到最后一个 } 的片段
        4. 直接就是 JSON
        """
        text = text.strip()

        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if fenced:
            return BlueprintValidator._decode_first_json_object(fenced.group(1).strip())

        return BlueprintValidator._decode_first_json_object(text)

    @staticmethod
    def get_tool_names_from_jsonl(tools_path: Path) -> set[str]:
        """
        从 tools.jsonl 提取所有工具名（name 字段）。
        """
        names: set[str] = set()

        if not tools_path.exists():
            return names

        for line in tools_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            if isinstance(obj, dict) and "name" in obj:
                names.add(str(obj["name"]))

        return names

    @classmethod
    def validate(
        cls,
        data: dict,
        allowed_tool_names: set[str] | None = None,
    ) -> list[str]:
        """
        校验 blueprint 格式，返回错误列表；空列表表示通过。
        """
        errors: list[str] = []

        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"缺少必填字段: {field}")

        for key in data:
            if key not in cls.ALLOWED_FIELDS:
                errors.append(f"存在未允许字段: {key}")

        for key in ("initial_state", "expected_final_state"):
            if key in data and data[key] is not None and not isinstance(data[key], dict):
                errors.append(f"{key} 必须为 JSON 对象或 null")

        steps = data.get("steps")
        if steps is None:
            errors.append("缺少必填字段: steps")
        elif not isinstance(steps, list):
            errors.append("steps 必须为数组")
        elif len(steps) == 0:
            errors.append("steps 不能为空，应至少包含一个步骤")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"steps[{i}] 必须为对象")
                    continue

                goal = step.get("goal")
                if not isinstance(goal, str) or not goal.strip():
                    errors.append(f"steps[{i}].goal 必须为非空字符串")

                tool_calls = step.get("possible_tool_calls")
                if not isinstance(tool_calls, list):
                    errors.append(f"steps[{i}].possible_tool_calls 必须为数组")
                else:
                    for j, name in enumerate(tool_calls):
                        if not isinstance(name, str) or not name.strip():
                            errors.append(
                                f"steps[{i}].possible_tool_calls[{j}] 必须为非空字符串"
                            )
                        elif allowed_tool_names is not None and name not in allowed_tool_names:
                            errors.append(
                                f"steps[{i}].possible_tool_calls 中含非法工具名: {name!r}，"
                                "应在 tools.jsonl 的 name 列表中"
                            )

        if "goals" in data:
            goals = data["goals"]
            if not isinstance(goals, list):
                errors.append("goals 必须为数组")
            elif len(goals) == 0:
                errors.append("goals 不能为空，应至少包含一个目标")
            else:
                for i, item in enumerate(goals):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"goals[{i}] 必须为非空字符串")

        if "possible_tool_calls" in data:
            ptc = data["possible_tool_calls"]
            goals = data.get("goals", [])

            if not isinstance(ptc, list):
                errors.append("possible_tool_calls 必须为数组")
            elif not all(isinstance(inner, list) for inner in ptc):
                errors.append("possible_tool_calls 必须为嵌套数组 [[tools],[tools],...]")
            elif len(ptc) != len(goals):
                errors.append(
                    f"possible_tool_calls 长度 ({len(ptc)}) 必须与 goals 长度 ({len(goals)}) 一致"
                )
            else:
                for i, inner in enumerate(ptc):
                    for j, name in enumerate(inner):
                        if not isinstance(name, str) or not name.strip():
                            errors.append(
                                f"possible_tool_calls[{i}][{j}] 必须为非空字符串"
                            )
                        elif allowed_tool_names is not None and name not in allowed_tool_names:
                            errors.append(
                                f"possible_tool_calls[{i}] 中含非法工具名: {name!r}，"
                                "应在 tools.jsonl 的 name 列表中"
                            )

        if "user_agent_config" in data:
            user_agent_config = data["user_agent_config"]
            if not isinstance(user_agent_config, dict):
                errors.append("user_agent_config 必须为对象")
            else:
                for key in cls.USER_AGENT_CONFIG_KEYS:
                    if key not in user_agent_config:
                        errors.append(f"user_agent_config 缺少字段: {key}")
                    elif not isinstance(user_agent_config[key], str) or not user_agent_config[key].strip():
                        errors.append(f"user_agent_config.{key} 必须为非空字符串")

        if "end_condition" in data:
            end_condition = data["end_condition"]
            if not isinstance(end_condition, str) or not end_condition.strip():
                errors.append("end_condition 必须为非空字符串")

        return errors

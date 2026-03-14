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
        "goals",
        "possible_tool_calls",
        "scenario_id",
        "environment_profile",
        "initial_state",
        "user_agent_config",
        "end_condition",
    ]

    ALLOWED_FIELDS = {
        "blueprint_id",
        "skill_name",
        "persona_id",
        "created_at",
        "goals",
        "possible_tool_calls",
        "scenario_id",
        "environment_profile",
        "initial_state",
        "expected_final_state",
        "state_checkpoints",
        "user_agent_config",
        "end_condition",
    }

    USER_AGENT_CONFIG_KEYS = ("role", "personality", "knowledge_boundary")

    @staticmethod
    def _load_first_json_object(text: str) -> dict:
        """
        从文本中解析第一个 JSON 对象，允许后面跟额外解释文字。
        """
        decoder = json.JSONDecoder()
        stripped = text.lstrip()
        obj, _ = decoder.raw_decode(stripped)
        if not isinstance(obj, dict):
            raise ValueError("blueprint 必须是 JSON 对象")
        return obj

    @staticmethod
    def _collect_json_object_candidates(text: str) -> list[dict]:
        """
        扫描文本中的所有 JSON 对象候选，避免错误选中前置的小对象。
        """
        decoder = json.JSONDecoder()
        candidates: list[dict] = []
        seen: set[tuple[str, ...]] = set()

        start = 0
        while True:
            start = text.find("{", start)
            if start == -1:
                break

            try:
                obj, _ = decoder.raw_decode(text[start:])
            except json.JSONDecodeError:
                start += 1
                continue

            if isinstance(obj, dict):
                key = tuple(sorted(obj.keys()))
                if key not in seen:
                    candidates.append(obj)
                    seen.add(key)

            start += 1

        return candidates

    @classmethod
    def _select_best_candidate(cls, candidates: list[dict]) -> dict:
        if not candidates:
            raise ValueError("未找到可解析的 blueprint JSON 对象")

        def sort_key(candidate: dict) -> tuple[int, int]:
            required_count = sum(1 for field in cls.REQUIRED_FIELDS if field in candidate)
            return (required_count, len(json.dumps(candidate, ensure_ascii=False)))

        return max(candidates, key=sort_key)

    @classmethod
    def extract_json_from_response(cls, text: str) -> dict:
        """
        从模型回复中提取 JSON。

        允许以下情况：
        1. ```json ... ```
        2. ``` ... ```
        3. 前后带说明文字，只取第一个 { 到最后一个 } 的片段
        4. 直接就是 JSON
        """
        text = text.strip()
        candidates: list[dict] = []

        fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        for block in fenced_blocks:
            candidates.extend(cls._collect_json_object_candidates(block.strip()))

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.extend(cls._collect_json_object_candidates(text[start : end + 1]))

        candidates.extend(cls._collect_json_object_candidates(text))
        if candidates:
            return cls._select_best_candidate(candidates)

        return cls._load_first_json_object(text)

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

        if "scenario_id" in data:
            scenario_id = data["scenario_id"]
            if not isinstance(scenario_id, str) or not scenario_id.strip():
                errors.append("scenario_id 必须为非空字符串")

        if "environment_profile" in data:
            profile = data["environment_profile"]
            if not isinstance(profile, dict):
                errors.append("environment_profile 必须为对象")
            else:
                backend_mode = profile.get("backend_mode")
                validation_mode = profile.get("validation_mode")
                if backend_mode is not None and backend_mode not in {
                    "program-direct",
                    "program-fixture",
                    "hybrid",
                    "llm-fallback",
                }:
                    errors.append(f"environment_profile.backend_mode 非法: {backend_mode}")
                if validation_mode is not None and validation_mode not in {
                    "none",
                    "final_state",
                    "turn_state",
                }:
                    errors.append(
                        f"environment_profile.validation_mode 非法: {validation_mode}"
                    )
                state_mutation_policy = profile.get("state_mutation_policy")
                if state_mutation_policy is not None and state_mutation_policy not in {
                    "programmatic",
                }:
                    errors.append(
                        "environment_profile.state_mutation_policy 非法: "
                        f"{state_mutation_policy}"
                    )
                generated_text_policy = profile.get("generated_text_policy")
                if generated_text_policy is not None and generated_text_policy not in {
                    "none",
                    "templated-summary",
                    "derived-text",
                }:
                    errors.append(
                        "environment_profile.generated_text_policy 非法: "
                        f"{generated_text_policy}"
                    )
                generated_fields = profile.get("generated_result_fields")
                if generated_fields is not None and not (
                    isinstance(generated_fields, list)
                    and all(isinstance(item, str) and item.strip() for item in generated_fields)
                ):
                    errors.append(
                        "environment_profile.generated_result_fields 必须为字符串数组"
                    )

        if "state_checkpoints" in data:
            checkpoints = data["state_checkpoints"]
            if checkpoints is not None and not isinstance(checkpoints, list):
                errors.append("state_checkpoints 必须为数组或 null")
            elif isinstance(checkpoints, list):
                for i, checkpoint in enumerate(checkpoints):
                    if not isinstance(checkpoint, dict):
                        errors.append(f"state_checkpoints[{i}] 必须为对象")
                        continue
                    if not isinstance(checkpoint.get("turn_index"), int):
                        errors.append(
                            f"state_checkpoints[{i}].turn_index 必须为整数"
                        )
                    if not isinstance(checkpoint.get("expected_state"), dict):
                        errors.append(
                            f"state_checkpoints[{i}].expected_state 必须为对象"
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
                if allowed_tool_names is not None and len(allowed_tool_names) > 1 and len(goals) < 2:
                    errors.append("多工具技能的 goals 应至少包含两个目标")

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
                    if allowed_tool_names is not None and len(allowed_tool_names) > 1 and len(inner) < 2:
                        errors.append(
                            f"多工具技能的 possible_tool_calls[{i}] 应至少包含两个工具"
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

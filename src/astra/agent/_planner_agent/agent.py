from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from ...envs.context import (
    load_environment_context,
    render_environment_summary,
    render_scenario_summary,
)
from ...utils import config as astra_config
from ...utils import logger

from .config import PlannerAgentConfig
from .prompt_builder import PlannerPromptBuilder
from .types import BlueprintResult, PlannerRunContext
from .validator import BlueprintValidator


OPENAI_REQUEST_TIMEOUT_SEC = 120.0


class PlannerAgent:
    """
    PlannerAgent：基于 prompt + SKILL.md + tools.jsonl + persona_text 调用模型生成 blueprint。

    职责：
    1. 解析 skill 目录
    2. 读取输入文件
    3. 构造 prompt
    4. 调用模型
    5. 提取 blueprint JSON
    6. 注入程序字段
    7. 返回结构化结果
    """

    def __init__(self, config: PlannerAgentConfig):
        self.config = config.normalized()
        self.prompt_builder = PlannerPromptBuilder(
            prompt_path=self.config.prompt_path,
        )

    def generate(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
    ) -> BlueprintResult:
        """
        生成 blueprint，返回结构化结果，不直接写文件。
        假定输入是正确的，不做额外校验。
        """
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))
        
        resolved_skill_dir = self.resolve_skill_dir(skill_dir)
        context = self.build_run_context(skill_dir=resolved_skill_dir)

        skill_content = context.skill_md_path.read_text(encoding="utf-8")
        tools_content = context.tools_jsonl_path.read_text(encoding="utf-8")

        prompt = self.prompt_builder.build(
            skill_md_content=skill_content,
            tools_jsonl_content=tools_content,
            persona_content=persona_text,
            environment_profile=render_environment_summary(
                {
                    "environment_profile": context.environment_profile_summary or {},
                }
            ),
            scenario_summary=render_scenario_summary(
                {"scenario_summary": context.scenario_summary or {}}
            ),
        )

        raw_response = self.call_model(prompt)
        allowed_tool_names = BlueprintValidator.get_tool_names_from_jsonl(
            context.tools_jsonl_path
        )
        try:
            normalized, raw_response = self.parse_validate_or_repair(
                raw_response=raw_response,
                prompt=prompt,
                skill_dir=context.skill_dir,
                persona_text=persona_text,
                allowed_tool_names=allowed_tool_names,
            )
        except ValueError as exc:
            logger.warning("Planner output repair failed; using deterministic fallback: {}", exc)
            normalized = self.build_fallback_blueprint(
                skill_dir=context.skill_dir,
                persona_text=persona_text,
                tools_jsonl_path=context.tools_jsonl_path,
            )
            raw_response = json.dumps(normalized, ensure_ascii=False)

        return BlueprintResult(
            blueprint=normalized,
            raw_response=raw_response,
            prompt=prompt,
            skill_dir=context.skill_dir,
            persona_text=persona_text,
        )

    def write_blueprint(self, blueprint: dict, output_path: Path) -> Path:
        """
        将 blueprint 写入 JSON 文件。
        """
        resolved_output = (
            output_path.resolve()
            if output_path.is_absolute()
            else (self.config.project_root / output_path).resolve()
        )
        resolved_output.parent.mkdir(parents=True, exist_ok=True)
        resolved_output.write_text(
            json.dumps(blueprint, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Blueprint written to: {}", resolved_output)
        return resolved_output

    def build_run_context(self, *, skill_dir: Path) -> PlannerRunContext:
        """
        构造本次运行上下文。
        假定输入路径正确，不做额外校验。
        """
        env_context = load_environment_context(skill_dir)

        return PlannerRunContext(
            skill_dir=skill_dir,
            skill_md_path=skill_dir / "SKILL.md",
            tools_jsonl_path=skill_dir / "tools.jsonl",
            environment_profile_path=(
                skill_dir / "environment_profile.json"
                if (skill_dir / "environment_profile.json").exists()
                else None
            ),
            scenario_dir=skill_dir / "scenarios" if (skill_dir / "scenarios").exists() else None,
            environment_profile_summary=env_context.get("environment_profile"),
            scenario_summary=env_context.get("scenario_summary"),
        )

    def resolve_skill_dir(self, skill_dir: Path) -> Path:
        """
        解析 skill 目录
        """
        if skill_dir.is_absolute():
            return skill_dir.resolve()
        return (self.config.project_root / skill_dir).resolve()

    def call_model(self, prompt: str) -> str:
        """
        调用大模型生成 blueprint 原始文本。
        """
        api_key = astra_config.get_planner_agent_api_key()
        model = astra_config.get_planner_agent_model()
        base_url = astra_config.get_planner_agent_base_url()

        logger.info("Calling planner model: {}", model)
        logger.debug("Planner prompt length: {} chars", len(prompt))

        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=OPENAI_REQUEST_TIMEOUT_SEC,
            max_retries=2,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        raw = response.choices[0].message.content or ""
        logger.debug("Planner raw response length: {} chars", len(raw))
        return raw

    def repair_model_output(
        self,
        *,
        prompt: str,
        raw_response: str,
        validation_errors: list[str],
    ) -> str:
        """
        当 planner 输出接近正确但未通过校验时，请模型只做 JSON 修复。
        """
        api_key = astra_config.get_planner_agent_api_key()
        model = astra_config.get_planner_agent_model()
        base_url = astra_config.get_planner_agent_base_url()

        repair_prompt = "\n\n".join(
            [
                "You repair malformed planner blueprint JSON.",
                "Return exactly one valid JSON object and nothing else.",
                "Do not include markdown, explanations, or <think> tags.",
                "Do not explain the errors. Do not repeat the malformed JSON.",
                "Preserve the original task intent and tool choices whenever possible.",
                "Prefer a minimal valid blueprint over a detailed but malformed one.",
                "If nested state is hard to express, use {} for expected_final_state and [] for state_checkpoints.",
                "Use only this schema:",
                '{'
                '"goals":["..."],'
                '"possible_tool_calls":[["tool_name_1","tool_name_2"]],'
                '"initial_state":{},'
                '"expected_final_state":{},'
                '"state_checkpoints":[],'
                '"user_agent_config":{"role":"...","personality":"...","knowledge_boundary":"..."},'
                '"end_condition":"..."'
                '}',
                "If the skill has multiple meaningful tools, use multiple goals and give each goal 2-3 realistic tool options.",
                "Do not output scenario_id or environment_profile; those fields are injected later.",
                "Validation errors from the first pass:",
                "\n".join(f"- {item}" for item in validation_errors),
                "Original planner prompt for intent reference:",
                prompt,
                "Malformed planner response:",
                raw_response,
            ]
        )

        logger.info("Repairing planner output after validation failure")
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=OPENAI_REQUEST_TIMEOUT_SEC,
            max_retries=2,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": repair_prompt}],
            temperature=0.0,
        )
        repaired = response.choices[0].message.content or ""
        logger.debug("Planner repaired response length: {} chars", len(repaired))
        return repaired

    def parse_validate_or_repair(
        self,
        *,
        raw_response: str,
        prompt: str,
        skill_dir: Path,
        persona_text: str,
        allowed_tool_names: set[str],
    ) -> tuple[dict, str]:
        """
        解析并校验 planner 输出；必要时触发一次修复回路。
        """
        last_errors: list[str] = []
        candidate_response = raw_response

        for attempt in range(2):
            parsed = BlueprintValidator.extract_json_from_response(candidate_response)
            enriched = self.inject_program_fields(
                parsed,
                skill_dir=skill_dir,
                persona_text=persona_text,
            )
            normalized = self.normalize_blueprint(
                enriched,
                available_tool_names=sorted(allowed_tool_names),
            )
            validation_errors = BlueprintValidator.validate(
                normalized,
                allowed_tool_names=allowed_tool_names,
            )
            if not validation_errors:
                return normalized, candidate_response

            last_errors = validation_errors
            if attempt == 0:
                candidate_response = self.repair_model_output(
                    prompt=prompt,
                    raw_response=candidate_response,
                    validation_errors=validation_errors,
                )
                continue

        raise ValueError("蓝图格式校验失败: " + "; ".join(last_errors))

    def build_fallback_blueprint(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
        tools_jsonl_path: Path,
    ) -> dict:
        """
        当模型两次都无法产出合法蓝图时，用工具 schema 合成最小可用蓝图。
        """
        persona_obj = json.loads(persona_text)
        persona_desc = str(persona_obj.get("persona", "")).strip() or "A general user"
        role = persona_desc
        if role.lower().startswith("a "):
            role = role[2:]
        elif role.lower().startswith("an "):
            role = role[3:]
        role = role[:120] or "user"

        tool_specs: list[dict] = []
        for line in tools_jsonl_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("name"), str):
                tool_specs.append(obj)

        selected_tools = tool_specs[: max(1, min(4, len(tool_specs)))]
        ordered_tool_names = [
            str(spec["name"]).strip()
            for spec in selected_tools
            if str(spec.get("name", "")).strip()
        ]
        goal_tool_sets: list[list[str]] = []
        if len(ordered_tool_names) <= 1:
            goal_tool_sets = [[ordered_tool_names[0]]] if ordered_tool_names else [[]]
        else:
            candidate_sets = [
                ordered_tool_names[: min(3, len(ordered_tool_names))],
                ordered_tool_names[:1] + ordered_tool_names[1 : min(4, len(ordered_tool_names))],
                ordered_tool_names[-2:] + ordered_tool_names[:1],
                ordered_tool_names[-3:],
            ]
            seen_sets: set[tuple[str, ...]] = set()
            for candidate in candidate_sets:
                merged: list[str] = []
                for name in candidate:
                    if name and name not in merged:
                        merged.append(name)
                if len(merged) < 2:
                    continue
                marker = tuple(merged)
                if marker in seen_sets:
                    continue
                seen_sets.add(marker)
                goal_tool_sets.append(merged)
            if not goal_tool_sets:
                goal_tool_sets = [ordered_tool_names[: min(2, len(ordered_tool_names))]]

        goals: list[str] = []
        possible_tool_calls: list[list[str]] = []
        descriptions = {
            str(spec["name"]).strip(): str(spec.get("description", "")).strip()
            for spec in selected_tools
            if str(spec.get("name", "")).strip()
        }
        for tool_set in goal_tool_sets:
            joined_tools = ", ".join(tool_set)
            detail_parts = [
                descriptions[name].rstrip(".")
                for name in tool_set
                if descriptions.get(name)
            ][:2]
            if detail_parts:
                goal = (
                    f"Use {joined_tools} together to make progress on the "
                    f"{skill_dir.name.replace('-', ' ')} task: {'; '.join(detail_parts)}"
                )
            else:
                goal = (
                    f"Use {joined_tools} together to make progress on the "
                    f"{skill_dir.name.replace('-', ' ')} task"
                )
            goals.append(goal)
            possible_tool_calls.append(tool_set)

        if not goals:
            goals = [f"Make progress on the {skill_dir.name.replace('-', ' ')} task"]
            possible_tool_calls = [[]]

        blueprint = {
            "goals": goals,
            "possible_tool_calls": possible_tool_calls,
            "initial_state": {},
            "expected_final_state": {},
            "state_checkpoints": [],
            "user_agent_config": {
                "role": role,
                "personality": f"Acts consistently with the persona: {persona_desc}",
                "knowledge_boundary": (
                    "Knows their own goals and domain context, but does not know "
                    "tool names, APIs, or backend implementation details."
                ),
            },
            "end_condition": (
                f"The user has completed the planned {skill_dir.name.replace('-', ' ')} workflow "
                "and has no further questions."
            ),
        }

        enriched = self.inject_program_fields(
            blueprint,
            skill_dir=skill_dir,
            persona_text=persona_text,
        )
        normalized = self.normalize_blueprint(
            enriched,
            available_tool_names=sorted(
                BlueprintValidator.get_tool_names_from_jsonl(tools_jsonl_path)
            ),
        )
        validation_errors = BlueprintValidator.validate(
            normalized,
            allowed_tool_names=BlueprintValidator.get_tool_names_from_jsonl(
                tools_jsonl_path
            ),
        )
        if validation_errors:
            raise ValueError("Fallback 蓝图格式校验失败: " + "; ".join(validation_errors))
        return normalized

    def inject_program_fields(
        self,
        blueprint: dict,
        *,
        skill_dir: Path,
        persona_text: str,
    ) -> dict:
        """
        注入程序控制字段。
        """
        persona_obj = json.loads(persona_text)

        data = dict(blueprint)
        data["blueprint_id"] = str(uuid.uuid4())
        data["skill_name"] = skill_dir.name
        data["persona_id"] = persona_obj.get("id", "")
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        env_context = load_environment_context(skill_dir)
        if env_context:
            data["scenario_id"] = env_context.get("scenario_id", "default")
            data["environment_profile"] = {
                "backend_mode": env_context["environment_profile"].get("backend_mode"),
                "validation_mode": env_context["environment_profile"].get(
                    "validation_mode"
                ),
            }
            data.setdefault("initial_state", {})
            data.setdefault("expected_final_state", {})
            data.setdefault("state_checkpoints", [])

        return data

    def normalize_blueprint(
        self,
        blueprint: dict,
        *,
        available_tool_names: list[str] | None = None,
    ) -> dict:
        """
        对 blueprint 做轻量后处理。

        当前规则：
        - 若 initial_state 为对象，且其所有值均为空对象/空数组/null，
          则移除 expected_final_state。
        - 若顶层误返回 role/personality/knowledge_boundary，则收拢到 user_agent_config
        - 若多工具技能只返回一个 goal，则自动补成至少两个 goal
        - 若 possible_tool_calls 与 goals 数量不一致，则按最后一组工具补齐或截断
        - 若 possible_tool_calls 过窄（单工具行过多），则按邻近 goal 自动扩成多工具
        - 若 state_checkpoints 结构异常，则回落为 []
        """
        data = dict(blueprint)
        initial_state = data.get("initial_state")
        stray_user_fields = {
            key: data.pop(key)
            for key in ("role", "personality", "knowledge_boundary")
            if isinstance(data.get(key), str) and data.get(key).strip()
        }

        if stray_user_fields and "user_agent_config" not in data:
            data["user_agent_config"] = stray_user_fields

        goals = data.get("goals")
        possible_tool_calls = data.get("possible_tool_calls")
        tool_pool = [
            str(name).strip()
            for name in (available_tool_names or [])
            if isinstance(name, str) and str(name).strip()
        ]
        if isinstance(goals, list):
            normalized_goals = [
                item.strip()
                for item in goals
                if isinstance(item, str) and item.strip()
            ]
            if len(normalized_goals) == 1 and len(tool_pool) > 1:
                base_goal = normalized_goals[0]
                normalized_goals = [
                    base_goal,
                    f"Verify or refine the result for: {base_goal}",
                ]
            data["goals"] = normalized_goals
            goals = normalized_goals
        if isinstance(goals, list) and isinstance(possible_tool_calls, list):
            normalized_tool_calls = [
                item if isinstance(item, list) else []
                for item in possible_tool_calls
            ]
            if normalized_tool_calls:
                filler = normalized_tool_calls[-1] or tool_pool[: min(2, len(tool_pool))]
            else:
                filler = tool_pool[: min(2, len(tool_pool))]
            while len(normalized_tool_calls) < len(goals):
                normalized_tool_calls.append(list(filler))
            if len(normalized_tool_calls) > len(goals):
                normalized_tool_calls = normalized_tool_calls[: len(goals)]

            normalized_tool_calls = [
                [
                    str(name).strip()
                    for name in group
                    if isinstance(name, str) and str(name).strip()
                ]
                for group in normalized_tool_calls
            ]
            unique_tool_names: list[str] = []
            for group in normalized_tool_calls:
                for name in group:
                    if name not in unique_tool_names:
                        unique_tool_names.append(name)
            for name in tool_pool:
                if name not in unique_tool_names:
                    unique_tool_names.append(name)

            if len(unique_tool_names) > 1:
                expanded_tool_calls: list[list[str]] = []
                for index, group in enumerate(normalized_tool_calls):
                    merged: list[str] = []
                    neighbor_groups = [group]
                    if index > 0:
                        neighbor_groups.append(normalized_tool_calls[index - 1])
                    if index + 1 < len(normalized_tool_calls):
                        neighbor_groups.append(normalized_tool_calls[index + 1])
                    neighbor_groups.append(unique_tool_names)

                    for source in neighbor_groups:
                        for name in source:
                            if name not in merged:
                                merged.append(name)
                            if len(merged) >= min(3, len(unique_tool_names)):
                                break
                        if len(merged) >= min(3, len(unique_tool_names)):
                            break

                    if len(merged) < 2:
                        for name in unique_tool_names:
                            if name not in merged:
                                merged.append(name)
                            if len(merged) >= min(2, len(unique_tool_names)):
                                break

                    expanded_tool_calls.append(merged)

                normalized_tool_calls = expanded_tool_calls

            data["possible_tool_calls"] = normalized_tool_calls

        if not isinstance(data.get("state_checkpoints"), list):
            data["state_checkpoints"] = []

        if isinstance(initial_state, dict):
            if all(value == [] or value == {} or value is None for value in initial_state.values()):
                data.pop("expected_final_state", None)

        return data

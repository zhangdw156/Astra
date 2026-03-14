from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from ...utils import config as astra_config
from ...utils import logger

from .config import PlannerAgentConfig
from .prompt_builder import PlannerPromptBuilder
from .types import BlueprintResult, PlannerRunContext
from .validator import BlueprintValidator


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
        )

        allowed_tool_names = BlueprintValidator.get_tool_names_from_jsonl(
            context.tools_jsonl_path
        )
        raw_response = self.call_model(prompt)
        normalized_input, validation_errors = self.parse_and_validate_blueprint(
            raw_response,
            allowed_tool_names=allowed_tool_names,
        )
        if validation_errors:
            logger.warning(
                "Planner blueprint invalid, attempting repair: {}",
                "; ".join(validation_errors),
            )
            repair_prompt = self.build_repair_prompt(
                raw_response=raw_response,
                validation_errors=validation_errors,
                allowed_tool_names=allowed_tool_names,
            )
            repaired_raw_response = self.call_model(repair_prompt)
            repaired_input, repair_errors = self.parse_and_validate_blueprint(
                repaired_raw_response,
                allowed_tool_names=allowed_tool_names,
            )
            if repair_errors:
                raise ValueError("蓝图格式校验失败: " + "; ".join(repair_errors))

            raw_response = repaired_raw_response
            normalized_input = repaired_input

        enriched = self.inject_program_fields(
            normalized_input,
            skill_dir=context.skill_dir,
            persona_text=persona_text,
        )
        normalized = self.normalize_blueprint(enriched)

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
        return PlannerRunContext(
            skill_dir=skill_dir,
            skill_md_path=skill_dir / "SKILL.md",
            tools_jsonl_path=skill_dir / "tools.jsonl",
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

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.model_temperature,
        )

        raw = response.choices[0].message.content or ""
        logger.debug("Planner raw response length: {} chars", len(raw))
        return raw

    def parse_and_validate_blueprint(
        self,
        raw_response: str,
        *,
        allowed_tool_names: set[str],
    ) -> tuple[dict[str, Any], list[str]]:
        try:
            parsed = BlueprintValidator.extract_json_from_response(raw_response)
        except json.JSONDecodeError as exc:
            return {}, [f"未能从模型回复中提取 JSON: {exc.msg}"]

        normalized_input = BlueprintValidator.normalize(
            parsed,
            allowed_tool_names=allowed_tool_names,
        )
        validation_errors = BlueprintValidator.validate(
            normalized_input,
            allowed_tool_names=allowed_tool_names,
        )
        return normalized_input, validation_errors

    def build_repair_prompt(
        self,
        *,
        raw_response: str,
        validation_errors: list[str],
        allowed_tool_names: set[str],
    ) -> str:
        valid_tools_block = "\n".join(
            f"- {name}" for name in sorted(allowed_tool_names)
        )
        errors_block = "\n".join(f"- {item}" for item in validation_errors)

        return f"""You are repairing an invalid task blueprint JSON.

Return exactly one corrected JSON object and nothing else.

Valid tool names from tools.jsonl:
{valid_tools_block}

Observed validation errors:
{errors_block}

Invalid model output to repair:
{raw_response}

Repair rules:
- Preserve the original skill intent and persona alignment as much as possible.
- Use the `steps` schema, where each item contains exactly one `goal` and that goal's `possible_tool_calls`.
- Keep `goals` and `possible_tool_calls` aligned with `steps`.
- Use only valid tool names from the list above.
- If the invalid output mentions unsupported tool-like names, replace them by redesigning the step around the valid tools instead of inventing aliases.
- If multiple tools contribute to one user-facing goal, keep them in the same step instead of creating extra steps.
- Keep the blueprint concise and structurally valid.
"""

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

        return data

    def normalize_blueprint(self, blueprint: dict) -> dict:
        """
        对 blueprint 做轻量后处理。

        当前规则：
        - 若 initial_state 为对象，且其所有值均为空对象/空数组/null，
          则移除 expected_final_state。
        """
        data = dict(blueprint)
        initial_state = data.get("initial_state")

        if isinstance(initial_state, dict):
            if all(value == [] or value == {} or value is None for value in initial_state.values()):
                data.pop("expected_final_state", None)

        return data

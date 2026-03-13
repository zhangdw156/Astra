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
        parsed = BlueprintValidator.extract_json_from_response(raw_response)

        allowed_tool_names = BlueprintValidator.get_tool_names_from_jsonl(
            context.tools_jsonl_path
        )
        validation_errors = BlueprintValidator.validate(
            parsed,
            allowed_tool_names=allowed_tool_names,
        )
        if validation_errors:
            raise ValueError("蓝图格式校验失败: " + "; ".join(validation_errors))

        enriched = self.inject_program_fields(
            parsed,
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

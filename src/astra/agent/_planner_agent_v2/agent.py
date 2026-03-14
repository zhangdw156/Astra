from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from ...utils import logger
from .._planner_agent.agent import PlannerAgent
from .._planner_agent.config import PlannerAgentConfig
from .._planner_agent.types import BlueprintResult
from .._planner_agent.validator import BlueprintValidator
from .._skill_agent.executor import OpenCodeExecutor, SubprocessOpenCodeExecutor

from .config import PlannerAgentV2Config
from .prompt_builder import PlannerPromptBuilderV2


class PlannerAgentV2:
    """
    PlannerAgentV2：通过 OpenCode 检查 skill 目录并直接产出 blueprint 文件。
    """

    def __init__(
        self,
        config: PlannerAgentV2Config,
        executor: OpenCodeExecutor | None = None,
    ):
        self.config = config.normalized()
        self.executor = executor or SubprocessOpenCodeExecutor()
        self.prompt_builder = PlannerPromptBuilderV2(self.config.prompt_path)
        self.legacy = PlannerAgent(
            PlannerAgentConfig(
                prompt_path=self.config.prompt_path,
                project_root=self.config.project_root,
                verbose=self.config.verbose,
            )
        )

    def generate(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
    ) -> BlueprintResult:
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        resolved_skill_dir = self.legacy.resolve_skill_dir(skill_dir)
        context = self.legacy.build_run_context(skill_dir=resolved_skill_dir)
        allowed_tool_names = BlueprintValidator.get_tool_names_from_jsonl(
            context.tools_jsonl_path
        )

        temp_root = self.config.project_root / ".planner_agent_v2_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="planner_agent_v2_", dir=temp_root))
        output_path = temp_dir / "blueprint.json"
        prompt = self.build_task_text(
            skill_dir=context.skill_dir,
            persona_text=persona_text,
            output_path=output_path,
        )

        try:
            exit_code = self.invoke_opencode(prompt)
            if exit_code != 0:
                raise RuntimeError(f"OpenCode 执行失败，exit code={exit_code}")

            raw_response, normalized = self.load_validate_or_repair_output(
                output_path=output_path,
                prompt=prompt,
                skill_dir=context.skill_dir,
                persona_text=persona_text,
                allowed_tool_names=allowed_tool_names,
            )
        except Exception as exc:
            logger.warning("PlannerAgentV2 failed; using deterministic fallback: {}", exc)
            normalized = self.legacy.build_fallback_blueprint(
                skill_dir=context.skill_dir,
                persona_text=persona_text,
                tools_jsonl_path=context.tools_jsonl_path,
            )
            raw_response = json.dumps(normalized, ensure_ascii=False)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return BlueprintResult(
            blueprint=normalized,
            raw_response=raw_response,
            prompt=prompt,
            skill_dir=context.skill_dir,
            persona_text=persona_text,
            output_path=None,
        )

    def write_blueprint(self, blueprint: dict, output_path: Path) -> Path:
        return self.legacy.write_blueprint(blueprint, output_path)

    def build_task_text(
        self,
        *,
        skill_dir: Path,
        persona_text: str,
        output_path: Path,
    ) -> str:
        return self.prompt_builder.build(
            skill_dir=str(skill_dir.resolve()),
            persona_content=persona_text,
            output_path=str(output_path.resolve()),
            output_schema=self.output_schema_text(),
            available_capabilities=self.available_capabilities_text(),
            required_files_guide=self.required_files_guide_text(),
            planning_workflow=self.planning_workflow_text(),
            blueprint_rules=self.blueprint_rules_text(),
            scenario_alignment_rules=self.scenario_alignment_rules_text(),
            fallback_policy=self.fallback_policy_text(),
        )

    def invoke_opencode(self, task_text: str) -> int:
        logger.debug("Invoking: opencode run <planner_v2_task>")
        return self.executor.run(
            task_text=task_text,
            cwd=self.config.project_root,
            verbose=self.config.verbose,
        )

    def load_validate_or_repair_output(
        self,
        *,
        output_path: Path,
        prompt: str,
        skill_dir: Path,
        persona_text: str,
        allowed_tool_names: set[str],
    ) -> tuple[str, dict]:
        last_errors: list[str] = []
        raw_response = self.read_output_file(output_path)

        for attempt in range(self.config.repair_attempts + 1):
            parsed = BlueprintValidator.extract_json_from_response(raw_response)
            enriched = self.legacy.inject_program_fields(
                parsed,
                skill_dir=skill_dir,
                persona_text=persona_text,
            )
            normalized = self.legacy.normalize_blueprint(
                enriched,
                available_tool_names=sorted(allowed_tool_names),
            )
            normalized = self.sanitize_expected_states(normalized)
            validation_errors = BlueprintValidator.validate(
                normalized,
                allowed_tool_names=allowed_tool_names,
            )
            if not validation_errors:
                return raw_response, normalized

            last_errors = validation_errors
            if attempt == self.config.repair_attempts:
                break

            self.repair_output_file(
                prompt=prompt,
                raw_response=raw_response,
                validation_errors=validation_errors,
                output_path=output_path,
            )
            raw_response = self.read_output_file(output_path)

        raise ValueError("蓝图格式校验失败: " + "; ".join(last_errors))

    def repair_output_file(
        self,
        *,
        prompt: str,
        raw_response: str,
        validation_errors: list[str],
        output_path: Path,
    ) -> None:
        repair_task = "\n\n".join(
            [
                "Repair the planner blueprint file that you generated earlier.",
                f"Overwrite this file with exactly one valid JSON object: {output_path}",
                "Do not modify any other files.",
                "Preserve the original task intent whenever possible.",
                "The file must contain only JSON with no markdown or commentary.",
                "Validation errors:",
                "\n".join(f"- {item}" for item in validation_errors),
                "Original task text:",
                prompt,
                "Current invalid file content:",
                raw_response,
            ]
        )
        exit_code = self.invoke_opencode(repair_task)
        if exit_code != 0:
            raise RuntimeError(f"OpenCode repair failed，exit code={exit_code}")

    def read_output_file(self, output_path: Path) -> str:
        if not output_path.exists():
            raise FileNotFoundError(f"planner v2 未生成输出文件: {output_path}")
        return output_path.read_text(encoding="utf-8")

    def output_schema_text(self) -> str:
        return json.dumps(
            {
                "goals": ["..."],
                "possible_tool_calls": [["tool_name_1", "tool_name_2"]],
                "initial_state": {},
                "expected_final_state": {},
                "state_checkpoints": [],
                "user_agent_config": {
                    "role": "...",
                    "personality": "...",
                    "knowledge_boundary": "...",
                },
                "end_condition": "...",
            },
            ensure_ascii=False,
            indent=2,
        )

    def available_capabilities_text(self) -> str:
        return "\n".join(
            [
                "- You may inspect the repository and read files under the skill directory.",
                "- You may compare SKILL.md, tools.jsonl, environment_profile.json, scenarios, and backend.py.",
                "- You must write the final blueprint JSON to the requested output path.",
                "- Do not edit skill files, prompts, or any file other than the blueprint output path.",
            ]
        )

    def required_files_guide_text(self) -> str:
        return "\n".join(
            [
                "Inspect these files first if they exist:",
                "1. SKILL.md",
                "2. tools.jsonl",
                "3. environment_profile.json",
                "4. scenarios/default.json or the active scenario file",
                "5. backend.py",
            ]
        )

    def planning_workflow_text(self) -> str:
        return "\n".join(
            [
                "1. Read the skill files to understand the real tool contract and environment.",
                "2. Infer a conservative, executable workflow that matches the persona.",
                "3. Produce a blueprint JSON that aligns with the real scenario and tool constraints.",
                "4. Write the final JSON to the output path and stop.",
            ]
        )

    def blueprint_rules_text(self) -> str:
        return "\n".join(
            [
                "- Use only tools that exist in tools.jsonl.",
                "- For multi-tool skills, prefer at least two ordered goals when realistic.",
                "- Keep goals natural and user-centric, not API-centric.",
                "- expected_final_state should describe structural outcomes, not invented factual results.",
                "- In expected_final_state, avoid exact free-form message text unless the skill requires literal text matching.",
                "- Prefer placeholders like non-empty strings, ids, or appended items over exact timestamps or exact wording.",
                "- state_checkpoints should usually be [] unless an intermediate state truly matters.",
                "- The output file must contain only one JSON object.",
            ]
        )

    def scenario_alignment_rules_text(self) -> str:
        return "\n".join(
            [
                "- For program-fixture skills, align initial_state with the real scenario or a minimal faithful subset.",
                "- Do not invent phone numbers, message IDs, timestamps, account IDs, or messages that are absent from the scenario.",
                "- If the environment exposes a default or primary resource, prefer workflows that use it.",
                "- If a precise expected_final_state would require guessing execution results, keep it minimal or empty.",
                "- For messaging skills, validate success structurally: an outbound message exists, the source and destination are plausible, and counters advance.",
            ]
        )

    def fallback_policy_text(self) -> str:
        return "\n".join(
            [
                "- If skill files disagree, prefer the most conservative workflow supported by the real tool schema.",
                "- If scenario details are unclear, keep initial_state/expected_final_state minimal rather than inventing specifics.",
                "- Never block on perfection; produce a valid, conservative blueprint file.",
            ]
        )

    def sanitize_expected_states(self, blueprint: dict) -> dict:
        sanitized = dict(blueprint)
        expected = sanitized.get("expected_final_state")
        if isinstance(expected, dict):
            sanitized["expected_final_state"] = self._sanitize_state_value(
                expected,
                parent_key="expected_final_state",
            )

        checkpoints = sanitized.get("state_checkpoints")
        if isinstance(checkpoints, list):
            new_checkpoints: list[dict] = []
            for checkpoint in checkpoints:
                if not isinstance(checkpoint, dict):
                    continue
                expected_state = checkpoint.get("expected_state")
                if not isinstance(expected_state, dict):
                    new_checkpoints.append(checkpoint)
                    continue
                updated = dict(checkpoint)
                updated["expected_state"] = self._sanitize_state_value(
                    expected_state,
                    parent_key="expected_state",
                )
                new_checkpoints.append(updated)
            sanitized["state_checkpoints"] = new_checkpoints
        return sanitized

    def _sanitize_state_value(self, value: object, *, parent_key: str) -> object:
        if isinstance(value, dict):
            result: dict[str, object] = {}
            for key, item in value.items():
                lowered = str(key).lower()
                if lowered in {"timestamp", "created_at", "updated_at", "sent_at"}:
                    continue
                if lowered in {"id", "blueprint_id", "trajectory_id"}:
                    continue
                if lowered in {"message", "content", "text"} and isinstance(item, str):
                    result[key] = {"nonempty": True}
                    continue
                result[key] = self._sanitize_state_value(item, parent_key=lowered)
            return result

        if isinstance(value, list):
            return [self._sanitize_state_value(item, parent_key=parent_key) for item in value]

        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"non_empty_array", "nonempty_array", "non-empty-array"}:
                return [{}]
            if lowered in {"non_empty_object", "nonempty_object", "non-empty-object"}:
                return {}
            if lowered in {"non_empty_string", "nonempty_string", "non-empty-string"}:
                return {"nonempty": True}
            if parent_key in {"did", "dst", "to", "from", "direction", "status", "primary_did"}:
                return value
            if len(value) > 32 or " " in value:
                return {"nonempty": True}
            return value

        return value

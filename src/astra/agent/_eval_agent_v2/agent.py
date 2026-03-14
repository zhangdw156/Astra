from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ...utils import logger
from .._eval_agent.agent import EvalAgent
from .._eval_agent.config import EvalAgentConfig
from .._eval_agent.prompt_builder import EvalAgentPromptBuilder
from .._eval_agent.types import EvaluationBundle, EvaluationResult
from .._eval_agent.validator import EvalAgentValidator
from .._skill_agent.executor import OpenCodeExecutor, SubprocessOpenCodeExecutor

from .config import EvalAgentV2Config
from .exporters import build_qwen3_sft_record
from .prompt_builder import EvalPromptBuilderV2
from .review_validator import EvalReviewValidator


class EvalAgentV2:
    """
    EvalAgentV2：通过 OpenCode 检查 skill 目录并直接产出 evaluation 文件。
    """

    def __init__(
        self,
        config: EvalAgentV2Config,
        executor: OpenCodeExecutor | None = None,
    ):
        self.config = config.normalized()
        self.executor = executor or SubprocessOpenCodeExecutor()
        self.prompt_builder = EvalPromptBuilderV2(self.config.prompt_path)
        legacy_prompt_path = self.config.project_root / "src/astra/prompts/eval_agent.md"
        if not legacy_prompt_path.exists():
            legacy_prompt_path = self.config.prompt_path
        self.sanitizer = EvalAgentPromptBuilder(
            prompt_path=legacy_prompt_path,
            max_message_chars=self.config.max_message_chars,
        )
        self.legacy = EvalAgent(
            EvalAgentConfig(
                prompt_path=legacy_prompt_path,
                max_message_chars=self.config.max_message_chars,
            )
        )

    def evaluate(
        self,
        *,
        trajectory: dict,
        blueprint: dict,
        skill_dir: Path | None = None,
    ) -> EvaluationBundle:
        config_errors = self.config.validate_basic()
        if config_errors:
            raise ValueError("; ".join(config_errors))

        resolved_skill_dir = self.resolve_skill_dir(trajectory=trajectory, skill_dir=skill_dir)
        clean_blueprint = self.sanitizer.sanitize_blueprint_for_eval(blueprint)
        clean_trajectory = self.sanitizer.sanitize_trajectory_for_eval(trajectory)

        temp_root = self.config.project_root / ".eval_agent_v2_tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="eval_agent_v2_", dir=temp_root))
        blueprint_path = temp_dir / "blueprint.json"
        trajectory_path = temp_dir / "trajectory.json"
        evaluation_output_path = temp_dir / "evaluation.json"
        review_output_path = temp_dir / "review.json"
        blueprint_path.write_text(
            json.dumps(clean_blueprint, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        trajectory_path.write_text(
            json.dumps(clean_trajectory, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        task_text = self.build_task_text(
            skill_dir=resolved_skill_dir,
            blueprint_path=blueprint_path,
            trajectory_path=trajectory_path,
            evaluation_output_path=evaluation_output_path,
            review_output_path=review_output_path,
        )

        try:
            exit_code = self.invoke_opencode(task_text)
            if exit_code != 0:
                raise RuntimeError(f"OpenCode 执行失败，exit code={exit_code}")

            raw_response, parsed, review = self.load_validate_or_repair_output(
                evaluation_output_path=evaluation_output_path,
                review_output_path=review_output_path,
                task_text=task_text,
            )
        except Exception as exc:
            logger.warning("EvalAgentV2 failed; using legacy eval fallback: {}", exc)
            return self.legacy.evaluate(trajectory=trajectory, blueprint=blueprint)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        result = self.build_evaluation_result(
            parsed=parsed,
            blueprint=blueprint,
            trajectory=trajectory,
            review=review,
        )
        artifacts = self.build_artifacts(
            blueprint=blueprint,
            trajectory=trajectory,
            review=review,
            result=result,
        )
        return EvaluationBundle(
            result=result,
            prompt=task_text,
            raw_response=raw_response,
            artifacts=artifacts or None,
        )

    def resolve_skill_dir(self, *, trajectory: dict, skill_dir: Path | None) -> Path:
        if skill_dir is not None:
            return skill_dir.resolve()
        embedded = trajectory.get("skill_dir")
        if isinstance(embedded, str) and embedded.strip():
            return Path(embedded).resolve()
        skill_name = str(trajectory.get("skill_name", "")).strip()
        if skill_name:
            candidate = self.config.project_root / "artifacts" / "env_top30_skills" / skill_name
            if candidate.exists():
                return candidate.resolve()
        return self.config.project_root

    def build_task_text(
        self,
        *,
        skill_dir: Path,
        blueprint_path: Path,
        trajectory_path: Path,
        evaluation_output_path: Path,
        review_output_path: Path,
    ) -> str:
        return self.prompt_builder.build(
            skill_dir=str(skill_dir.resolve()),
            blueprint_path=str(blueprint_path.resolve()),
            trajectory_path=str(trajectory_path.resolve()),
            evaluation_output_path=str(evaluation_output_path.resolve()),
            review_output_path=str(review_output_path.resolve()),
            evaluation_schema=self.evaluation_schema_text(),
            review_schema=self.review_schema_text(),
            available_capabilities=self.available_capabilities_text(),
            evaluation_workflow=self.evaluation_workflow_text(),
            evaluation_rules=self.evaluation_rules_text(),
            repair_policy=self.repair_policy_text(),
        )

    def invoke_opencode(self, task_text: str) -> int:
        logger.debug("Invoking: opencode run <eval_v2_task>")
        return self.executor.run(
            task_text=task_text,
            cwd=self.config.project_root,
            verbose=self.config.verbose,
        )

    def load_validate_or_repair_output(
        self,
        *,
        evaluation_output_path: Path,
        review_output_path: Path,
        task_text: str,
    ) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
        last_errors: list[str] = []
        raw_response = self.read_output_file(evaluation_output_path)

        for attempt in range(self.config.repair_attempts + 1):
            parsed = EvalAgentValidator.extract_json_from_response(raw_response)
            parsed = EvalAgentValidator.normalize(parsed)
            validation_errors = EvalAgentValidator.validate(parsed)
            if not validation_errors:
                review = self.load_review(review_output_path)
                return raw_response, parsed, review

            last_errors = validation_errors
            if attempt == self.config.repair_attempts:
                break

            self.repair_output_file(
                task_text=task_text,
                raw_response=raw_response,
                validation_errors=validation_errors,
                evaluation_output_path=evaluation_output_path,
            )
            raw_response = self.read_output_file(evaluation_output_path)

        raise ValueError("评估结果格式校验失败: " + "; ".join(last_errors))

    def repair_output_file(
        self,
        *,
        task_text: str,
        raw_response: str,
        validation_errors: list[str],
        evaluation_output_path: Path,
    ) -> None:
        repair_task = "\n\n".join(
            [
                "Repair the evaluation file that you generated earlier.",
                f"Overwrite this file with exactly one valid JSON object: {evaluation_output_path}",
                "Do not modify any other files.",
                "The file must contain only JSON with no markdown or commentary.",
                "Validation errors:",
                "\n".join(f"- {item}" for item in validation_errors),
                "Original task text:",
                task_text,
                "Current invalid evaluation file content:",
                raw_response,
            ]
        )
        exit_code = self.invoke_opencode(repair_task)
        if exit_code != 0:
            raise RuntimeError(f"OpenCode repair failed，exit code={exit_code}")

    def read_output_file(self, output_path: Path) -> str:
        if not output_path.exists():
            raise FileNotFoundError(f"eval v2 未生成输出文件: {output_path}")
        return output_path.read_text(encoding="utf-8")

    def load_review(self, review_output_path: Path) -> dict[str, Any] | None:
        if not self.config.write_review_artifact or not review_output_path.exists():
            return None

        try:
            raw = review_output_path.read_text(encoding="utf-8")
            parsed = EvalAgentValidator.extract_json_from_response(raw)
        except Exception as exc:
            logger.warning("Eval review parse failed: {}", exc)
            return None

        normalized = EvalReviewValidator.normalize(parsed)
        errors = EvalReviewValidator.validate(normalized)
        if errors:
            logger.warning("Eval review validation failed: {}", "; ".join(errors))
            return None
        return normalized

    def build_evaluation_result(
        self,
        *,
        parsed: dict[str, Any],
        blueprint: dict,
        trajectory: dict,
        review: dict[str, Any] | None,
    ) -> EvaluationResult:
        diagnostics = {
            "final_state_match": trajectory.get("validation", {}).get("final_state_match"),
            "state_checkpoints": trajectory.get("validation", {}).get("state_checkpoints"),
        }
        if review is not None:
            diagnostics["eval_review"] = review

        return EvaluationResult(
            score=float(parsed["score"]),
            hallucination_risk=str(parsed["hallucination_risk"]),
            task_completion_score=float(parsed["task_completion_score"]),
            reason=str(parsed["reason"]).strip(),
            run_id=str(trajectory.get("run_id", "")),
            blueprint_id=str(blueprint.get("blueprint_id", "")),
            trajectory_id=str(trajectory.get("trajectory_id", "")),
            diagnostics=diagnostics,
        )

    def build_artifacts(
        self,
        *,
        blueprint: dict,
        trajectory: dict,
        review: dict[str, Any] | None,
        result: EvaluationResult,
    ) -> dict[str, Any]:
        artifacts: dict[str, Any] = {}
        if review is not None:
            artifacts["review"] = review

        repair_plan = self.assess_repair_candidate(review=review, result=result)
        if repair_plan is not None:
            artifacts["repair_report"] = repair_plan
            artifacts["repair_markdown"] = self.render_repair_markdown(
                repair_plan=repair_plan,
                blueprint=blueprint,
                trajectory=trajectory,
                result=result,
            )

        should_export = (
            self.config.export_repair_dataset_artifact
            and repair_plan is not None
            and bool(review is not None and review.get("export_training_artifact"))
        )
        if not should_export:
            return artifacts

        artifacts["training_export"] = {
            "format": "qwen3_tool_calling_sft_repair_candidate",
            "repair_target": repair_plan.get("repair_target", "none"),
            "repair_strategy": repair_plan.get("repair_strategy", ""),
            "review_summary": repair_plan.get("summary", ""),
            "source": {
                "run_id": result.run_id,
                "blueprint_id": result.blueprint_id,
                "trajectory_id": result.trajectory_id,
            },
            "blueprint": blueprint,
            "trajectory_qwen3_sft": build_qwen3_sft_record(trajectory),
        }
        return artifacts

    def assess_repair_candidate(
        self,
        *,
        review: dict[str, Any] | None,
        result: EvaluationResult,
    ) -> dict[str, Any] | None:
        if review is None:
            return None
        if not bool(review.get("should_repair")):
            return None

        repair_target = str(review.get("repair_target", "none")).strip() or "none"
        if repair_target == "none":
            return None

        repair_strategy = str(review.get("repair_strategy", "")).strip()
        if not repair_strategy:
            return None

        if result.hallucination_risk in {"medium", "high"}:
            return None
        if result.task_completion_score < 0.5:
            return None

        score = float(result.score)
        if score < 1.5:
            return None

        root_causes = review.get("root_causes", [])
        if not isinstance(root_causes, list):
            root_causes = []

        return {
            "run_id": result.run_id,
            "blueprint_id": result.blueprint_id,
            "trajectory_id": result.trajectory_id,
            "score": score,
            "hallucination_risk": result.hallucination_risk,
            "task_completion_score": result.task_completion_score,
            "repair_target": repair_target,
            "repair_strategy": repair_strategy,
            "root_causes": [str(item).strip() for item in root_causes if str(item).strip()],
            "summary": str(review.get("summary", "")).strip(),
            "strongest_positive": str(review.get("strongest_positive", "")).strip(),
            "strongest_negative": str(review.get("strongest_negative", "")).strip(),
            "worth_repairing": True,
            "repair_readiness": "ready_for_future_repair_agent",
        }

    def render_repair_markdown(
        self,
        *,
        repair_plan: dict[str, Any],
        blueprint: dict,
        trajectory: dict,
        result: EvaluationResult,
    ) -> str:
        skill_name = str(trajectory.get("skill_name", "")).strip()
        root_causes = repair_plan.get("root_causes", [])
        causes_text = ", ".join(root_causes) if root_causes else "(unspecified)"
        return "\n".join(
            [
                "# Repair Plan",
                "",
                "## Status",
                "- worth_repairing: true",
                f"- repair_target: {repair_plan.get('repair_target', 'none')}",
                f"- repair_readiness: {repair_plan.get('repair_readiness', '')}",
                "",
                "## Source",
                f"- skill_name: {skill_name}",
                f"- blueprint_id: {repair_plan.get('blueprint_id', '')}",
                f"- trajectory_id: {repair_plan.get('trajectory_id', '')}",
                f"- run_id: {repair_plan.get('run_id', '')}",
                "",
                "## Evaluation Snapshot",
                f"- score: {result.score}",
                f"- hallucination_risk: {result.hallucination_risk}",
                f"- task_completion_score: {result.task_completion_score}",
                "",
                "## Why Repair Is Worthwhile",
                f"- summary: {repair_plan.get('summary', '') or '(missing)'}",
                f"- strongest_positive: {repair_plan.get('strongest_positive', '') or '(missing)'}",
                f"- strongest_negative: {repair_plan.get('strongest_negative', '') or '(missing)'}",
                f"- root_causes: {causes_text}",
                "",
                "## Recommended Repair Scope",
                f"- target: {repair_plan.get('repair_target', 'none')}",
                f"- strategy: {repair_plan.get('repair_strategy', '') or '(missing)'}",
                "",
                "## Invariants",
                "- Do not overwrite the original blueprint.json, trajectory.json, or evaluation.json.",
                "- Prefer sidecar patched artifacts such as blueprint_patched.json or trajectory_patched.json.",
                "- Preserve the visible task intent and tool-grounded facts.",
                "- Do not fabricate new tool outputs or new user goals.",
                "",
                "## Candidate Outputs For Future Repair Agent",
                "- repair_report.json",
                "- repair_training_export.json",
                "- blueprint_patched.json or trajectory_patched.json when safe",
                "",
                "## Context",
                f"- blueprint_goal_count: {len(blueprint.get('goals', [])) if isinstance(blueprint.get('goals'), list) else 0}",
                f"- final_state_match: {trajectory.get('validation', {}).get('final_state_match')}",
            ]
        )

    def evaluation_schema_text(self) -> str:
        return json.dumps(
            {
                "score": 0.0,
                "hallucination_risk": "none",
                "task_completion_score": 0.0,
                "reason": "",
            },
            ensure_ascii=False,
            indent=2,
        )

    def review_schema_text(self) -> str:
        return json.dumps(
            {
                "summary": "",
                "strongest_positive": "",
                "strongest_negative": "",
                "root_causes": ["planner"],
                "should_repair": False,
                "repair_target": "none",
                "repair_strategy": "",
                "export_training_artifact": False,
            },
            ensure_ascii=False,
            indent=2,
        )

    def available_capabilities_text(self) -> str:
        return "\n".join(
            [
                "- You may inspect the repository and read files under the skill directory.",
                "- You may compare SKILL.md, tools.jsonl, environment_profile.json, scenarios, and backend.py.",
                "- You may read the prepared blueprint and trajectory JSON files.",
                "- You must write the final evaluation JSON to the requested output path.",
                "- You may optionally write the review JSON to the requested review path.",
                "- Do not edit any files other than the requested output paths.",
            ]
        )

    def evaluation_workflow_text(self) -> str:
        return "\n".join(
            [
                "1. Read the skill files to understand the real environment contract.",
                "2. Read the prepared blueprint and trajectory JSON files.",
                "3. Evaluate sample quality across planner, user, assistant, and state correctness.",
                "4. Write one strict evaluation JSON object to the evaluation output path.",
                "5. If helpful, write a separate structured review JSON to the review output path.",
            ]
        )

    def evaluation_rules_text(self) -> str:
        return "\n".join(
            [
                "- Judge the visible sample as data quality, not just assistant fluency.",
                "- Use the skill files to disambiguate whether a planner mismatch is a real quality defect or a formatting artifact.",
                "- Minor structural blueprint issues should lower score modestly, not trigger fabricated failures.",
                "- If the trajectory is substantively correct but repairable, say so in the review instead of over-penalizing.",
                "- The required evaluation JSON must contain only the four schema fields.",
                "- `score` must use the 0.0 to 5.0 scale and must not be normalized to 0.0 to 1.0.",
                "- `task_completion_score` is the only field that uses the 0.0 to 1.0 range.",
                "- If you describe a sample as strong, high-quality, successful, grounded, or fully completed, `score` should usually be at least 4.0.",
                "- Reserve scores near 1.0 for severely flawed samples, not successful ones.",
            ]
        )

    def repair_policy_text(self) -> str:
        return "\n".join(
            [
                "- Only recommend repair for minor, local, recoverable defects.",
                "- Do not repair by editing the source trajectory or blueprint files.",
                "- Use repair_target=trajectory when the trajectory is good enough for downstream conversion but needs normalization.",
                "- Use export_training_artifact=true only when the sample is still useful after targeted normalization or relabeling.",
            ]
        )

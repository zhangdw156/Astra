from __future__ import annotations

from pathlib import Path


class EvalPromptBuilderV2:
    """
    负责基于模板渲染 eval v2 的 task text。
    """

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def build(
        self,
        *,
        skill_dir: str,
        blueprint_path: str,
        trajectory_path: str,
        evaluation_output_path: str,
        review_output_path: str,
        evaluation_schema: str,
        review_schema: str,
        available_capabilities: str,
        evaluation_workflow: str,
        evaluation_rules: str,
        repair_policy: str,
    ) -> str:
        return (
            self.template_text.replace("{SKILL_DIR}", skill_dir)
            .replace("{BLUEPRINT_PATH}", blueprint_path)
            .replace("{TRAJECTORY_PATH}", trajectory_path)
            .replace("{EVALUATION_OUTPUT_PATH}", evaluation_output_path)
            .replace("{REVIEW_OUTPUT_PATH}", review_output_path)
            .replace("{EVALUATION_SCHEMA}", evaluation_schema)
            .replace("{REVIEW_SCHEMA}", review_schema)
            .replace("{AVAILABLE_CAPABILITIES}", available_capabilities)
            .replace("{EVALUATION_WORKFLOW}", evaluation_workflow)
            .replace("{EVALUATION_RULES}", evaluation_rules)
            .replace("{REPAIR_POLICY}", repair_policy)
        )

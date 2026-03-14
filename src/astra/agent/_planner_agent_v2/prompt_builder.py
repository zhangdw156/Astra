from __future__ import annotations

from pathlib import Path


class PlannerPromptBuilderV2:
    """
    负责基于模板渲染 planner v2 的 task text。
    """

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def build(
        self,
        *,
        skill_dir: str,
        persona_content: str,
        output_path: str,
        output_schema: str,
        available_capabilities: str,
        required_files_guide: str,
        planning_workflow: str,
        blueprint_rules: str,
        scenario_alignment_rules: str,
        fallback_policy: str,
    ) -> str:
        return (
            self.template_text.replace("{SKILL_DIR}", skill_dir)
            .replace("{PERSONA_CONTENT}", persona_content)
            .replace("{OUTPUT_PATH}", output_path)
            .replace("{OUTPUT_SCHEMA}", output_schema)
            .replace("{AVAILABLE_CAPABILITIES}", available_capabilities)
            .replace("{REQUIRED_FILES_GUIDE}", required_files_guide)
            .replace("{PLANNING_WORKFLOW}", planning_workflow)
            .replace("{BLUEPRINT_RULES}", blueprint_rules)
            .replace("{SCENARIO_ALIGNMENT_RULES}", scenario_alignment_rules)
            .replace("{FALLBACK_POLICY}", fallback_policy)
        )

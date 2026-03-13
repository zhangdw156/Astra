from __future__ import annotations

from pathlib import Path


class PlannerPromptBuilder:
    """
    负责基于模板渲染 planner prompt。

    当前支持的占位符：
    - {SKILL_MD_CONTENT}
    - {TOOLS_JSONL_CONTENT}
    - {PERSONA_CONTENT}
    - {ENVIRONMENT_PROFILE}
    - {SCENARIO_SUMMARY}
    """

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def build(
        self,
        *,
        skill_md_content: str,
        tools_jsonl_content: str,
        persona_content: str,
        environment_profile: str = "(no environment profile)",
        scenario_summary: str = "(no scenario summary)",
    ) -> str:
        """
        使用已准备好的文本内容渲染 prompt。
        """
        return (
            self.template_text.replace("{SKILL_MD_CONTENT}", skill_md_content)
            .replace("{TOOLS_JSONL_CONTENT}", tools_jsonl_content)
            .replace("{PERSONA_CONTENT}", persona_content)
            .replace("{ENVIRONMENT_PROFILE}", environment_profile)
            .replace("{SCENARIO_SUMMARY}", scenario_summary)
        )

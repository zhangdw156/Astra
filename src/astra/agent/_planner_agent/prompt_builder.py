from __future__ import annotations

import json
import re
from pathlib import Path


class PlannerPromptBuilder:
    """
    负责基于模板渲染 planner prompt。

    当前支持的占位符：
    - {SKILL_MD_CONTENT}
    - {TOOLS_JSONL_CONTENT}
    - {PERSONA_CONTENT}
    """

    DOC_TOOL_NAME_PATTERN = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_tool_names_from_jsonl(tools_jsonl_content: str) -> list[str]:
        names: list[str] = []

        for line in tools_jsonl_content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            name = obj.get("name") if isinstance(obj, dict) else None
            if not isinstance(name, str):
                continue

            normalized = name.strip()
            if normalized and normalized not in names:
                names.append(normalized)

        return names

    @classmethod
    def _extract_doc_tool_names(cls, skill_md_content: str) -> list[str]:
        names: list[str] = []
        for match in cls.DOC_TOOL_NAME_PATTERN.findall(skill_md_content):
            if match not in names:
                names.append(match)
        return names

    @classmethod
    def _build_runtime_notes(
        cls,
        *,
        skill_md_content: str,
        tools_jsonl_content: str,
    ) -> str:
        allowed_tool_names = cls._extract_tool_names_from_jsonl(tools_jsonl_content)
        doc_tool_names = cls._extract_doc_tool_names(skill_md_content)
        unsupported_doc_names = [
            name for name in doc_tool_names if name not in allowed_tool_names
        ]

        lines = [
            "",
            "## Planner Runtime Notes",
            "",
            "Use only these exact tool names from tools.jsonl:",
        ]
        lines.extend(f"- `{name}`" for name in allowed_tool_names)

        if unsupported_doc_names:
            lines.extend(
                [
                    "",
                    "The following tool-like names appear in SKILL.md but are not valid tools. Never use them in the blueprint:",
                ]
            )
            lines.extend(f"- `{name}`" for name in unsupported_doc_names)

        lines.extend(
            [
                "",
                "Additional repair constraints:",
                "- Group multiple internal tools under the same user-facing goal instead of creating one step per tool.",
                "- If a documented capability is not backed by a valid tool name, redesign the goal around the valid tools instead of inventing aliases.",
            ]
        )
        return "\n".join(lines)

    def build(
        self,
        *,
        skill_md_content: str,
        tools_jsonl_content: str,
        persona_content: str,
    ) -> str:
        """
        使用已准备好的文本内容渲染 prompt。
        """
        augmented_skill_md = (
            skill_md_content
            + self._build_runtime_notes(
                skill_md_content=skill_md_content,
                tools_jsonl_content=tools_jsonl_content,
            )
        )
        return (
            self.template_text.replace("{SKILL_MD_CONTENT}", augmented_skill_md)
            .replace("{TOOLS_JSONL_CONTENT}", tools_jsonl_content)
            .replace("{PERSONA_CONTENT}", persona_content)
        )

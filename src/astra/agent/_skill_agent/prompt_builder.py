from __future__ import annotations

from pathlib import Path


class PromptBuilder:
    """
    负责从 prompt 模板构造 task text。

    当前支持的占位符：
    - {SKILL_DIR}
    - {EXAMPLE_DIR}
    """

    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path
        self.template_text = self.prompt_path.read_text(encoding="utf-8")

    def build(self, *, skill_dir: Path, example_dir: Path) -> str:
        """
        使用初始化时缓存的模板文本做占位符替换。
        """
        return (
            self.template_text.replace("{SKILL_DIR}", str(skill_dir.resolve()))
            .replace("{EXAMPLE_DIR}", str(example_dir.resolve()))
        )
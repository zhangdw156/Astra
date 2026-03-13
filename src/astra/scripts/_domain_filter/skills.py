"""Skill 目录枚举与内容读取。"""

import re
from pathlib import Path

# 单条 skill 内容长度上限（字符），超出则截断并注明，避免超 context
MAX_SKILL_CONTENT_CHARS = 80_000
MAX_SCRIPT_SUMMARY_FILES = 10


def skill_name_from_dirname(dirname: str) -> str:
    """从目录名去掉前缀序号，如 1_filehost -> filehost。"""
    return re.sub(r"^\d+_", "", dirname).strip() or dirname


def read_skill_content(skill_dir: Path) -> str:
    """
    读取 skill 目录的 name + SKILL.md 全部内容。
    若不存在 SKILL.md，仅返回目录名（name）；若 SKILL.md 过长则截断并注明。
    """
    name = skill_name_from_dirname(skill_dir.name)
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return f"Skill name: {name}\n(无 SKILL.md，仅以目录名判断)\n"

    try:
        raw = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"Skill name: {name}\n(无法读取 SKILL.md)\n"

    if len(raw) > MAX_SKILL_CONTENT_CHARS:
        raw = raw[:MAX_SKILL_CONTENT_CHARS] + "\n\n[... 内容已截断，超过长度上限 ...]"

    return f"Skill name: {name}\n\n--- SKILL.md 内容 ---\n\n{raw}"


def summarize_scripts(skill_dir: Path, max_files: int = MAX_SCRIPT_SUMMARY_FILES) -> str:
    """生成轻量 scripts 摘要：列出常见脚本文件相对路径。"""
    allow_ext = {
        ".py",
        ".sh",
        ".js",
        ".ts",
        ".mjs",
        ".cjs",
        ".go",
        ".rs",
        ".java",
        ".rb",
        ".php",
        ".ps1",
    }
    candidates: list[str] = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(skill_dir).as_posix()
        if rel.startswith("."):
            continue
        if rel.endswith("SKILL.md") or rel.endswith("README.md"):
            continue
        if p.suffix.lower() not in allow_ext:
            continue
        candidates.append(rel)
        if len(candidates) >= max_files:
            break

    if not candidates:
        return "(no script files found)"
    return "\n".join(f"- {item}" for item in candidates)


def list_skill_dirs(skills_root: Path) -> list[Path]:
    """列出 skills 根目录下所有子目录（视为 skill 目录），排除非目录与 README 等。"""
    skills_root = skills_root.resolve()
    if not skills_root.is_dir():
        return []
    return [p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith(".")]

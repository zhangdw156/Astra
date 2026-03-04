#!/usr/bin/env python3
"""
根据 Hydra 配置中的仓库列表 YAML，仅更新项目根目录的 .gitmodules 文件。

入口使用 @hydra.main()；不执行 git submodule add 或 clone。更新后需在仓库根执行
`git submodule update --init --recursive` 拉取 submodule。
"""

import re
from pathlib import Path
from typing import Any

import hydra
from loguru import logger
from omegaconf import DictConfig, OmegaConf

# 仓库根目录：含 .git 与 .gitmodules
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # scripts -> astra -> src -> root
GITMODULES = PROJECT_ROOT / ".gitmodules"

GITHUB_URL_PATTERN = re.compile(
    r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    return url.rstrip("/")


def parse_github_url(url: str) -> tuple[str, str] | None:
    m = GITHUB_URL_PATTERN.match(normalize_url(url))
    if not m:
        return None
    return (m.group(1), m.group(2))


def submodule_path_rel(owner: str, repo: str) -> str:
    return f"skillshub/{owner}_{repo}"


def parse_gitmodules(path: Path) -> list[tuple[str, str, str]]:
    """返回 [(section_name, path, url), ...]，均为相对路径。"""
    if not path.exists():
        return []
    entries = []
    current_name = current_path = current_url = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line_strip = line.strip()
        if line.startswith("[submodule "):
            if current_name is not None and current_path and current_url:
                entries.append((current_name, current_path, current_url))
            m = re.match(r'\[submodule\s+"([^"]+)"\]', line)
            current_name = m.group(1) if m else None
            current_path = current_url = None
        elif current_name is not None:
            if line_strip.startswith("path ="):
                current_path = line_strip.split("=", 1)[1].strip()
            elif line_strip.startswith("url ="):
                current_url = line_strip.split("=", 1)[1].strip()
    if current_name is not None and current_path and current_url:
        entries.append((current_name, current_path, current_url))
    return entries


def write_gitmodules(path: Path, entries: list[tuple[str, str, str]]) -> None:
    """按 Git 习惯写 .gitmodules（section、path、url，相对路径）。"""
    lines = []
    for name, sub_path, url in entries:
        lines.append(f'[submodule "{name}"]')
        lines.append(f"\tpath = {sub_path}")
        lines.append(f"\turl = {url}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def load_repos_from_config(conf: Any) -> list[str]:
    """从 OmegaConf/Hydra 解析出的配置中取仓库 URL 列表。支持 repos / repositories 或顶层 list。"""
    if conf is None:
        return []
    if OmegaConf.is_list(conf):
        return [str(u) for u in conf if u is not None and str(u).strip()]
    for key in ("repos", "repositories"):
        if key in conf and OmegaConf.is_list(conf[key]):
            return [str(u) for u in conf[key] if u is not None and str(u).strip()]
    return []


# Hydra 配置在项目根 configs/（astra 包内不放置 configs）
_CONFIG_DIR = PROJECT_ROOT / "configs"


@hydra.main(
    config_path=str(_CONFIG_DIR),
    config_name="update_gitmodules",
    version_base=None,
)
def main(cfg: DictConfig[str, Any]) -> None:
    """Hydra 入口：根据 cfg.repos_file 指向的 YAML 更新 .gitmodules。"""
    if not (PROJECT_ROOT / ".git").exists():
        logger.error("不在 Git 仓库根目录: {}", PROJECT_ROOT)
        raise SystemExit(1)

    repos_file = Path(cfg.repos_file)
    if not repos_file.is_absolute():
        repos_file = PROJECT_ROOT / repos_file
    if not repos_file.exists():
        logger.error("仓库列表文件不存在: {}", repos_file)
        raise SystemExit(1)

    conf = OmegaConf.load(repos_file)
    urls = load_repos_from_config(conf)
    if not urls:
        logger.warning("YAML 中未找到仓库列表（repos / repositories 或顶层 list）")
        return

    existing = parse_gitmodules(GITMODULES)
    seen_paths = {e[1] for e in existing}
    new_entries: list[tuple[str, str, str]] = list(existing)

    for raw_url in urls:
        url = normalize_url(raw_url)
        parsed = parse_github_url(url)
        if not parsed:
            logger.warning("跳过（非 GitHub URL）: {}", raw_url)
            continue
        owner, repo = parsed
        path_rel = submodule_path_rel(owner, repo)
        if path_rel in seen_paths:
            logger.debug("已存在: {}", path_rel)
            continue
        seen_paths.add(path_rel)
        new_entries.append((path_rel, path_rel, url))
        logger.info("添加: {} -> {}", url, path_rel)

    write_gitmodules(GITMODULES, new_entries)
    logger.info("已写入 {}（共 {} 条）", GITMODULES, len(new_entries))


if __name__ == "__main__":
    main()

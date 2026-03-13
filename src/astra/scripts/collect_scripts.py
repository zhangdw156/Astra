#!/usr/bin/env python3
"""
递归遍历 skillshub，将含有可执行 scripts 的目录复制到 skills。

仅保留 scripts 子目录下**全部**为 .py 或 .sh/.bash 脚本的目录：若某目录存在 scripts 且其中
至少有一个可执行脚本，且其中没有其它类型脚本（如 .js、.ts 等），则将该目录复制到 skills。

用法：
    uv run -m astra.scripts.collect_scripts
    uv run -m astra.scripts.collect_scripts mode=run
    uv run -m astra.scripts.collect_scripts --config-path=exps/skill_discovery/configs --config-name=collect_scripts mode=run
"""

import os
import shutil
import sys
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import get_original_cwd
from loguru import logger
from omegaconf import DictConfig

from astra.utils.logging import setup_logging

# 项目根目录（src/astra/scripts -> 上三级）
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

# Hydra 默认配置目录与名称
_config_path = str(PROJECT_ROOT / "exps" / "skill_discovery" / "configs")

# 可执行脚本的扩展名（用于判断是否为脚本文件）
EXECUTABLE_EXTENSIONS = {".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".jsx", ".tsx"}
# 仅保留 scripts 里全是以下类型脚本的目录
ALLOWED_SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".jsx", ".tsx"}


def _has_shebang(path: Path) -> bool:
    """检查文件是否含 shebang。"""
    try:
        with open(path, "rb") as f:
            first_line = f.readline().decode("utf-8", errors="ignore").strip()
        return first_line.startswith("#!")
    except (OSError, UnicodeDecodeError):
        return False


def _is_executable_script(path: Path) -> bool:
    """
    判断是否为可执行脚本。
    满足其一即可：有执行权限、有 shebang、或为常见脚本扩展名。
    """
    if not path.is_file() or path.name.startswith("."):
        return False
    if os.access(path, os.X_OK):
        return True
    if _has_shebang(path):
        return True
    if path.suffix.lower() in EXECUTABLE_EXTENSIONS:
        return True
    return False


def _scripts_only_py_or_shell(scripts_dir: Path) -> bool:
    """
    检查 scripts 目录下是否至少有一个可执行脚本，且全部为 .py 或 .sh/.bash。
    若存在 .js、.ts、.zsh 等其它类型可执行脚本则返回 False。
    """
    if not scripts_dir.is_dir():
        return False
    has_allowed = False
    for f in scripts_dir.iterdir():
        if not f.is_file() or not _is_executable_script(f):
            continue
        ext = f.suffix.lower()
        if ext not in ALLOWED_SCRIPT_EXTENSIONS:
            return False
        has_allowed = True
    return has_allowed


def _find_skill_dirs_with_scripts(skillshub_root: Path) -> list[Path]:
    """
    递归遍历 skillshub，返回「含有可执行 scripts 子目录」的目录列表。
    返回的是「包含 scripts 的父目录」，即要复制的目录。
    """
    skillshub_root = skillshub_root.resolve()
    if not skillshub_root.exists():
        logger.warning("skillshub 根目录不存在: {}", skillshub_root)
        return []

    result: list[Path] = []
    for root, dirs, _ in os.walk(skillshub_root, topdown=True):
        root_path = Path(root)
        if "scripts" in dirs:
            scripts_dir = root_path / "scripts"
            if _scripts_only_py_or_shell(scripts_dir):
                result.append(root_path)
                # 不再深入该目录的子目录，避免重复（子目录的 scripts 会单独遍历到）
                dirs.remove("scripts")
    return result


def _copy_dir(src: Path, dst: Path) -> None:
    """复制目录到目标，若目标已存在则覆盖。"""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    logger.info("已复制: {} -> {}", src, dst)


def run(cfg: DictConfig) -> int:
    """实际执行逻辑，接收 OmegaConf 配置。"""
    skillshub_root = Path(cfg.skillshub_root)
    skills_output = Path(cfg.skills_output)
    mode = str(cfg.mode).lower()

    # 相对路径基于调用时的目录（Hydra 会改 cwd，故用 get_original_cwd）
    base = Path(get_original_cwd())
    if not skillshub_root.is_absolute():
        skillshub_root = (base / skillshub_root).resolve()
    if not skills_output.is_absolute():
        skills_output = (base / skills_output).resolve()

    logger.info("skillshub_root: {}", skillshub_root)
    logger.info("skills_output: {}", skills_output)
    logger.info("mode: {}", mode)

    dirs_to_copy = _find_skill_dirs_with_scripts(skillshub_root)
    if not dirs_to_copy:
        logger.info("未发现含可执行 scripts 的目录")
        return 0

    logger.info("发现 {} 个目录含可执行 scripts", len(dirs_to_copy))
    skills_output.mkdir(parents=True, exist_ok=True)
    for idx, d in enumerate(dirs_to_copy, start=1):
        # 目标为 skills/<序号>_<目录名>，序号防止不同来源的同名 skill 覆盖
        basename = d.name
        dst = skills_output / f"{idx}_{basename}"
        if mode == "dry_run":
            logger.info("[dry_run] 将复制: {} -> {}", d, dst)
        else:
            _copy_dir(d, dst)

    return 0


@hydra.main(
    config_path=_config_path,
    config_name="collect_scripts",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    # 使用 astra 统一日志：Rich 控制台 + 写入 Hydra output_dir/run.log
    output_dir = HydraConfig.get().runtime.output_dir
    setup_logging(output_dir)
    sys.exit(run(cfg))


if __name__ == "__main__":
    main()

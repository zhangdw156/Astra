"""提示词模板加载；包内默认数据目录。"""

from pathlib import Path

# 包内默认数据目录（领域摘要 + filter_system.txt / filter_user.txt）
DATA_DIR = Path(__file__).resolve().parent / "data"

SYSTEM_FILENAME = "filter_system.txt"
USER_FILENAME = "filter_user.txt"


def load_prompt_templates(data_dir: Path) -> tuple[str, str]:
    """从数据目录加载 system 与 user 模板文件，返回 (system_template, user_template)。"""
    data_dir = data_dir.resolve()
    system_path = data_dir / SYSTEM_FILENAME
    user_path = data_dir / USER_FILENAME
    if not system_path.is_file():
        raise FileNotFoundError(f"系统提示词模板不存在: {system_path}")
    if not user_path.is_file():
        raise FileNotFoundError(f"用户提示词模板不存在: {user_path}")
    return system_path.read_text(encoding="utf-8"), user_path.read_text(encoding="utf-8")

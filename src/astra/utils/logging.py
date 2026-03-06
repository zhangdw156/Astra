"""
Loguru + Hydra 日志集成。

控制台与文件均使用纯文本格式，避免在 uv/子进程下打出裸 ANSI 码（如 [32m）。
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(output_dir: str | Path | None = None) -> None:
    """
    配置 loguru：控制台与文件均输出纯文本。

    当提供 output_dir（如 HydraConfig.get().runtime.output_dir）时，
    同时写入 {output_dir}/run.log。

    Args:
        output_dir: Hydra 任务输出目录路径。为 None 时仅配置控制台。
    """
    logger.remove()

    # 控制台：纯文本格式，避免在 zsh/uv 子进程下 ANSI 的 ESC 被丢弃后裸显 [32m 等
    logger.add(
        sys.stderr,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
        level="DEBUG",
    )

    # 文件输出：在 Hydra 环境下写入任务输出目录
    if output_dir is not None:
        log_path = Path(output_dir) / "run.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(log_path),
            colorize=False,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
                "{name}:{function}:{line} - {message}"
            ),
            level="DEBUG",
            rotation="10 MB",
        )
        logger.debug("Logging to file: {}", log_path)

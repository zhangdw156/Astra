"""
Loguru + Rich + Hydra 日志集成。

配置 loguru：输出到 Rich 控制台（彩色）；若提供 output_dir则同时写入该目录下 run.log。
"""

from pathlib import Path

from loguru import logger
from rich.console import Console


def setup_logging(output_dir: str | Path | None = None) -> None:
    """
    配置 loguru：Rich 控制台输出，并可选写入文件。

    当提供 output_dir（如 HydraConfig.get().runtime.output_dir）时，
    同时写入 {output_dir}/run.log。

    Args:
        output_dir: Hydra 任务输出目录路径。为 None 时仅配置控制台。
    """
    logger.remove()

    # Rich 控制台：彩色终端输出
    console = Console(stderr=True)
    logger.add(
        lambda msg: console.print(msg, end=""),
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
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

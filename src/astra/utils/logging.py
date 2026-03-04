"""
Loguru + Rich + Hydra logging integration.

Configures loguru to:
- Sink to Rich Console for beautiful, colorized terminal output
- Sink to Hydra's dynamic output directory when running under Hydra
"""

from pathlib import Path

from loguru import logger
from rich.console import Console


def setup_logging(output_dir: str | Path | None = None) -> None:
    """
    Configure loguru with Rich console output and optional file sink.

    When output_dir is provided (e.g. from HydraConfig.get().runtime.output_dir),
    logs are also written to {output_dir}/run.log.

    Args:
        output_dir: Path to Hydra's job output directory. If None, only
            console logging is configured.
    """
    logger.remove()

    # Rich console sink — colorized, beautiful terminal output
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

    # File sink — when running under Hydra, persist logs to output directory
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

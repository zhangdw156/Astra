"""
Astra CLI — Hydra-driven entry point.

All Astra entry points are designed to be invoked via @hydra.main.
Run with: astra or python -m astra.cli

Override config from CLI: astra skill.validation.strict_schema=false
"""

from pathlib import Path
from typing import Any

import hydra
from hydra.core.hydra_config import HydraConfig
from loguru import logger
from omegaconf import DictConfig

import astra
from astra.utils.logging import setup_logging
from astra.utils.ui import print_trace, welcome_dashboard


def run_app(cfg: DictConfig[str, Any]) -> None:
    """
    Main application logic — runs after Hydra config is loaded.

    Args:
        cfg: Hydra-composed configuration.
    """
    # Setup logging: Rich console + Hydra output directory
    output_dir = HydraConfig.get().runtime.output_dir
    setup_logging(output_dir)

    # 1. Welcome dashboard (Rich)
    welcome_dashboard(version=astra.__version__)

    # 2. Log config load event (Loguru)
    logger.info("Configuration loaded from Hydra")
    logger.debug("Output directory: {}", output_dir)
    logger.debug("Skill config: {}", dict(cfg.get("skill", {})))
    logger.debug("Agent config: {}", dict(cfg.get("agent", {})))

    # 3. Demo: pretty-print a sample tool trace (Rich)
    print_trace(
        tool_name="get_weather",
        tool_input={"location": "Beijing", "unit": "celsius"},
        tool_output={"temp": 22, "condition": "Sunny", "humidity": 45},
        turn=1,
    )

    logger.info("Astra proof-of-concept complete")


_CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@hydra.main(config_path=str(_CONFIG_DIR), config_name="config", version_base=None)
def main(cfg: DictConfig[str, Any]) -> None:
    """CLI entry point — invoked by Hydra with composed config."""
    run_app(cfg)


if __name__ == "__main__":
    main()

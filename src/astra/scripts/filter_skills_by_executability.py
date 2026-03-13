#!/usr/bin/env python3
"""
按可执行/可模拟性过滤 skills 的入口。

升级后的行为：
- run 模式下对不匹配的 skill 直接删除对应目录
- 基于 mockability / determinism / schema clarity / state complexity 等维度，
  对每个 skill 输出 richer schema
- 结果写入 jsonl，供后续与 domain filter 合并成统一 manifest

用法：
    uv run -m astra.scripts.filter_skills_by_executability
    uv run -m astra.scripts.filter_skills_by_executability mode=run
    uv run -m astra.scripts.filter_skills_by_executability mode=test
    uv run -m astra.scripts.filter_skills_by_executability mode=dry-run
    uv run -m astra.scripts.filter_skills_by_executability \
        --config-path=exps/skill_discovery/configs \
        --config-name=filter_by_executability \
        mode=run

需在项目根目录 .env 中配置：
- OPENAI_API_KEY
- OPENAI_MODEL
- 可选 OPENAI_BASE_URL
"""

from __future__ import annotations

import sys
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from astra.scripts._executability_filter import run
from astra.utils.logging import setup_logging

_config_path = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "exps"
    / "skill_discovery"
    / "configs"
)


@hydra.main(
    config_path=_config_path,
    config_name="filter_by_executability",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    output_dir = HydraConfig.get().runtime.output_dir
    setup_logging(output_dir)
    sys.exit(run(cfg))


if __name__ == "__main__":
    main()

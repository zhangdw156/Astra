#!/usr/bin/env python3
"""
按领域过滤/打分 skills 的入口。

升级后的行为：
- 不再默认在 run 模式下直接删除目录
- 基于 BFCL 风格 domain 相关性，对每个 skill 输出 richer schema：
  - match
  - reason
  - matched_domains
  - primary_domain
  - bfcl_relevance_score
  - domain_confidence
  - tool_call_intensity_score
  - multi_turn_potential_score
- 结果写入 jsonl，供后续与 executability filter 合并成统一 manifest

用法：
    uv run -m astra.scripts.filter_skills_by_domain
    uv run -m astra.scripts.filter_skills_by_domain mode=run
    uv run -m astra.scripts.filter_skills_by_domain mode=test
    uv run -m astra.scripts.filter_skills_by_domain mode=dry-run
    uv run -m astra.scripts.filter_skills_by_domain \
        --config-path=exps/skill_discovery/configs \
        --config-name=filter_by_domain \
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

from astra.scripts._domain_filter import run
from astra.utils.logging import setup_logging

# Hydra 默认配置目录与名称（项目根 exps/skill_discovery）
_config_path = str(
    Path(__file__).resolve().parent.parent.parent.parent
    / "exps"
    / "skill_discovery"
    / "configs"
)


@hydra.main(
    config_path=_config_path,
    config_name="filter_by_domain",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    output_dir = HydraConfig.get().runtime.output_dir
    setup_logging(output_dir)
    sys.exit(run(cfg))


if __name__ == "__main__":
    main()
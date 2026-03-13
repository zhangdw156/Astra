#!/usr/bin/env python3
"""
按领域过滤/打分 skills 的入口。

升级后的行为：
- run 模式下对不匹配的 skill 直接删除对应目录
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

用法（在项目根目录运行）：
    # 使用默认配置（src/astra/configs/filter_by_domain.yaml），dry-run 模式
    uv run -m astra.scripts.filter_skills_by_domain

    # 实际执行过滤并删除不匹配目录
    uv run -m astra.scripts.filter_skills_by_domain mode=run

    # 抽样少量 skill 做验证
    uv run -m astra.scripts.filter_skills_by_domain mode=test

需在项目根目录 .env 中配置：
- OPENAI_API_KEY
- OPENAI_MODEL
- 可选 OPENAI_BASE_URL
"""

from __future__ import annotations

import sys
from pathlib import Path

import hydra
from omegaconf import DictConfig

from ._domain_filter import run

# Hydra 默认配置目录与名称
_config_path = Path(__file__).resolve().parent.parent/ "configs"


@hydra.main(
    config_path=_config_path,
    config_name="filter_by_domain",
    version_base=None,
)
def main(cfg: DictConfig) -> None:
    sys.exit(run(cfg))


if __name__ == "__main__":
    main()
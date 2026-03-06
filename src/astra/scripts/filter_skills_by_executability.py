#!/usr/bin/env python3
"""
按“可执行性（docker-only + 可 mock）”过滤 skills：
- 输入：skills/ 下的 skill 目录
- 方式：读取 SKILL.md + scripts 概要，调用大模型判定 keep/drop
  - mode=dry-run：仅预览，不调用 API
  - mode=test：抽样调用 LLM，不做删除
  - mode=run：全量调用 LLM，并删除不保留的 skill 目录

用法：
  uv run -m astra.scripts.filter_skills_by_executability
  uv run -m astra.scripts.filter_skills_by_executability mode=dry-run
  uv run -m astra.scripts.filter_skills_by_executability mode=test skills_dir=skills_demo n_test=5
  uv run -m astra.scripts.filter_skills_by_executability mode=run
"""

import sys
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from astra.scripts._executability_filter import run
from astra.utils.logging import setup_logging

# Hydra 默认配置目录与名称（项目根 exps/skill_discovery）
_config_path = str(Path(__file__).resolve().parent.parent.parent.parent / "exps" / "skill_discovery" / "configs")


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


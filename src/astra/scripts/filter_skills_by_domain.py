#!/usr/bin/env python3
"""
按领域过滤 skills 的入口：基于 artifacts/multi_turn_func_doc 的领域描述，用 OpenAI 判断 skills/ 下各 skill
是否覆盖这些领域，只保留匹配的（不匹配的目录会被直接删除）。逻辑与提示词均在 astra.scripts._domain_filter 包内。

用法：
    uv run -m astra.scripts.filter_skills_by_domain
    uv run -m astra.scripts.filter_skills_by_domain mode=run
    uv run -m astra.scripts.filter_skills_by_domain mode=test   # 随机测试 3 个 skill，验证流程
    uv run -m astra.scripts.filter_skills_by_domain --config-path=exps/skill_discovery --config-name=filter_by_domain mode=run

需在项目根目录 .env 中配置：OPENAI_API_KEY、OPENAI_MODEL，可选 OPENAI_BASE_URL。
"""

import sys
from pathlib import Path

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from astra.scripts._domain_filter import run
from astra.utils.logging import setup_logging

# Hydra 默认配置目录与名称（项目根 exps/skill_discovery）
_config_path = str(Path(__file__).resolve().parent.parent.parent.parent / "exps" / "skill_discovery")


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

#!/usr/bin/env bash
# skill_discovery 实验：使用固定 Hydra 配置，从 skillshub 收集含可执行 scripts 的目录到 skills
# 用法：$0 [Hydra overrides...]
set -e
cd "$(dirname "$0")/../.."
uv run python -m astra.scripts.collect_scripts --config-path=exps/skill_discovery --config-name=collects "$@"

#!/usr/bin/env bash
# 使用固定 Hydra 配置更新 .gitmodules
# 用法：$0
set -e
cd "$(dirname "$0")/../.."
uv run python -m astra.scripts.update_gitmodules --config-path=exps/skill_collection --config-name=repos

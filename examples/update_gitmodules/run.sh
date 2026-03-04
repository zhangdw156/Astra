#!/usr/bin/env bash
# 在项目根目录执行：使用默认 configs/update_gitmodules.yaml 中的 repos_file
set -e
cd "$(dirname "$0")/../.."
uv run python -m astra.scripts.update_gitmodules

# 使用本示例的仓库列表时，可覆盖 repos_file：
# uv run python -m astra.scripts.update_gitmodules repos_file=examples/update_gitmodules/repos.example.yaml

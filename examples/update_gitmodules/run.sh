#!/usr/bin/env bash
# 示例：传入本目录下的 repos 文件，在项目根执行脚本
set -e
cd "$(dirname "$0")/../.."
uv run python -m astra.scripts.update_gitmodules examples/update_gitmodules/repos.example.yaml

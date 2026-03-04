#!/usr/bin/env bash
# 执行本实验的配置文件 exps/skill_collection/repos.yaml，更新 .gitmodules
# 通过 $0 解析脚本所在目录再 cd 到仓库根，从任意目录执行结果一致；Windows 下请用 Git Bash 或 WSL
set -e
cd "$(dirname "$0")/../.."
uv run python -m astra.scripts.update_gitmodules exps/skill_collection/repos.yaml

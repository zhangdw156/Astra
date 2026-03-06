#!/usr/bin/env bash
set -e
SCRIPT_PATH=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR/../.."
uv run -m astra.scripts.update_gitmodules --config-path=$SCRIPT_PATH --config-name=repos

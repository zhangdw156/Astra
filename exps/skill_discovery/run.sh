#!/usr/bin/env bash
set -e
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR/../.."
uv run -m astra.scripts.collect_scripts --config-path=$SCRIPT_DIR/configs --config-name=collect_scripts

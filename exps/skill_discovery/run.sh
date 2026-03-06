#!/usr/bin/env bash
set -e
SCRIPT_PATH=$(cd "$(dirname "$0")" && pwd)

uv run -m astra.scripts.collect_scripts --config-path=$SCRIPT_PATH --config-name=collects

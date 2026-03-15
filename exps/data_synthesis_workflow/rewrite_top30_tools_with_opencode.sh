#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILLS_ROOT="${1:-$ROOT_DIR/artifacts/env_top30_skills}"
SPEC_PATH="${2:-$ROOT_DIR/docs/tools_jsonl_rewrite_spec.md}"
LOG_ROOT="${3:-$ROOT_DIR/artifacts/tools_jsonl_rewrite_logs}"
TIMEOUT_SEC="${OPENCODE_TIMEOUT_SEC:-240}"

mkdir -p "$LOG_ROOT"

if [[ ! -d "$SKILLS_ROOT" ]]; then
  echo "skills root not found: $SKILLS_ROOT" >&2
  exit 1
fi

if [[ ! -f "$SPEC_PATH" ]]; then
  echo "spec file not found: $SPEC_PATH" >&2
  exit 1
fi

mapfile -t skill_dirs < <(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d | sort)

for skill_dir in "${skill_dirs[@]}"; do
  skill_name="$(basename "$skill_dir")"
  tools_path="$skill_dir/tools.jsonl"
  log_path="$LOG_ROOT/${skill_name}.log"

  if [[ ! -f "$tools_path" ]]; then
    echo "[$skill_name] skip: missing tools.jsonl" | tee "$log_path"
    continue
  fi

  echo "[$skill_name] rewriting $tools_path" | tee "$log_path"

  task_text=$(
    cat <<EOF
Rewrite the tools.jsonl file for this skill according to the repository spec below.

Spec file: $SPEC_PATH
Target skill directory: $skill_dir
Target file: $tools_path

Requirements:
- Read the spec file first and follow it strictly.
- Inspect SKILL.md and tools.jsonl in the target skill directory before editing.
- You may inspect other files in the skill directory only if needed to clarify the real tool contract.
- Only edit the target tools.jsonl file.
- Preserve one-valid-JSON-object-per-line format.
- Keep the same set of tool names.
- Improve tool descriptions and inputSchema parameter descriptions to reduce ambiguity.
- Do not add speculative tools or speculative parameters.
- Do not leave markdown fences or commentary in the file.
- Before finishing, re-open the rewritten tools.jsonl and verify it is valid JSONL.

When finished, stop.
EOF
  )

  set +e
  timeout "$TIMEOUT_SEC" opencode run "$task_text" --print-logs >>"$log_path" 2>&1
  opencode_status=$?
  set -e

  if [[ "$opencode_status" -ne 0 && "$opencode_status" -ne 124 ]]; then
    echo "[$skill_name] opencode failed with status $opencode_status; see $log_path" >&2
    exit 1
  fi

  if ! python3 - <<PY >>"$log_path" 2>&1
import json
from pathlib import Path
path = Path(r"$tools_path")
lines = path.read_text(encoding="utf-8").splitlines()
objs = [json.loads(line) for line in lines if line.strip()]
assert objs, "empty tools.jsonl"
assert all(isinstance(obj, dict) for obj in objs)
assert all("name" in obj and "description" in obj and "inputSchema" in obj for obj in objs)
print("validated", len(objs), "tools")
PY
  then
    echo "[$skill_name] validation failed; see $log_path" >&2
    exit 1
  fi

  if [[ "$opencode_status" -eq 124 ]]; then
    echo "[$skill_name] opencode hit timeout after ${TIMEOUT_SEC}s but output validated" | tee -a "$log_path"
  fi

  echo "[$skill_name] done" | tee -a "$log_path"
done

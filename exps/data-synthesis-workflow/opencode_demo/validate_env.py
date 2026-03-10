"""
单环境验证脚本，供 OpenCode 在生成 MCP 环境后自检质量。
验证：结构检查、uv sync、MCP Initialize 响应。
退出码：0=通过，1=失败。失败时输出具体错误，便于 OpenCode 修复后重试。

运行方式（OpenCode 应在生成完成后执行）：
  python exps/data-synthesis-workflow/opencode_demo/validate_env.py <ENV_DIR>

示例：
  python exps/data-synthesis-workflow/opencode_demo/validate_env.py env_demo/env_2515_stock-monitor
"""

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

MCP_INITIALIZE_REQUEST = b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"validate","version":"1.0"}}}\n'


def check_structure(env_dir: Path) -> tuple[bool, Optional[str]]:
    """
    结构检查：
    - strong 模式：mcp_server.py、tools/、pyproject.toml、database/、state.py
    - light/json-only 模式：mcp_server.py、pyproject.toml、tools.jsonl

    实际模式选择由 mcp_server.py 内部 ENV_MODE=strong|light|auto 控制，
    这里仅做静态存在性检查，允许两类环境通过。
    """
    mcp_server = env_dir / "mcp_server.py"
    pyproject = env_dir / "pyproject.toml"
    tools_dir = env_dir / "tools"
    database_dir = env_dir / "database"
    state_py = env_dir / "state.py"
    tools_jsonl = env_dir / "tools.jsonl"

    if not mcp_server.exists():
        return False, "missing mcp_server.py"
    if not pyproject.exists():
        return False, "missing pyproject.toml"

    # strong 路径：tools/ + database/ + state.py
    if tools_dir.exists() and database_dir.exists() and state_py.exists():
        return True, None

    # light 路径：tools.jsonl 存在即可（工具由 JSON Schema 驱动）
    if tools_jsonl.exists():
        return True, None

    return False, "missing tools/ + database/ + state.py (strong) or tools.jsonl (light)"


def run_uv_sync(env_dir: Path, timeout_sec: int = 120) -> tuple[bool, Optional[str]]:
    """运行 uv sync --no-install-project"""
    try:
        result = subprocess.run(
            ["uv", "sync", "--no-install-project"],
            cwd=env_dir,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()[:500]
            return False, f"uv sync failed (exit {result.returncode}): {err}"
        return True, None
    except subprocess.TimeoutExpired:
        return False, f"uv sync timeout ({timeout_sec}s)"


def run_mcp_initialize(env_dir: Path, timeout_sec: int = 10) -> tuple[bool, Optional[str]]:
    """启动 mcp_server，发送 initialize，解析 stdout 中的 JSON-RPC 响应"""
    proc = None

    def kill_if_timeout():
        if proc and proc.poll() is None:
            proc.kill()

    timer = threading.Timer(timeout_sec, kill_if_timeout)

    try:
        proc = subprocess.Popen(
            ["uv", "run", "python", "mcp_server.py"],
            cwd=env_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": str(env_dir)},
        )
        timer.start()
        stdout, stderr = proc.communicate(input=MCP_INITIALIZE_REQUEST, timeout=timeout_sec + 2)

        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("Loaded tool:") or line.startswith("Stock Monitor") or line.startswith("---"):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "result" in obj:
                    return True, None
                if isinstance(obj, dict) and "error" in obj:
                    return False, f"JSON-RPC error: {obj['error']}"
            except json.JSONDecodeError:
                continue

        err_msg = (stderr.decode("utf-8", errors="replace") or "").strip()[:300]
        return False, f"no valid JSON-RPC response" + (f"; stderr: {err_msg}" if err_msg else "")

    except subprocess.TimeoutExpired:
        if proc:
            proc.kill()
            proc.wait()
        return False, "MCP server timeout"
    except Exception as e:
        return False, str(e)[:300]
    finally:
        timer.cancel()
        if proc and proc.poll() is None:
            proc.kill()


def validate(env_dir: Path) -> tuple[bool, dict]:
    """验证单个 env，返回 (ok, result_dict)"""
    steps = {}
    error = None

    ok, err = check_structure(env_dir)
    steps["structure"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return False, {"ok": False, "steps": steps, "error": err}

    ok, err = run_uv_sync(env_dir)
    steps["uv_sync"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return False, {"ok": False, "steps": steps, "error": err}

    ok, err = run_mcp_initialize(env_dir)
    steps["mcp_initialize"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return False, {"ok": False, "steps": steps, "error": err}

    return True, {"ok": True, "steps": steps, "error": None}


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python validate_env.py <ENV_DIR>", file=sys.stderr)
        print("Example: python validate_env.py env_demo/env_2515_stock-monitor", file=sys.stderr)
        return 2

    env_dir = Path(sys.argv[1]).resolve()
    if not env_dir.exists():
        print(f"ERROR: Directory not found: {env_dir}", file=sys.stderr)
        return 2
    if not env_dir.is_dir():
        print(f"ERROR: Not a directory: {env_dir}", file=sys.stderr)
        return 2

    print(f"[validate_env] Checking: {env_dir}")
    ok, result = validate(env_dir)

    for step, status in result["steps"].items():
        print(f"  {step}: {status}")

    if ok:
        print("[validate_env] PASS - Environment is ready.")
        return 0
    else:
        print(f"[validate_env] FAIL - {result['error']}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
对 env_demo 下所有 MCP 环境执行可复现验证：结构检查、依赖安装、MCP 服务器 Initialize 响应。
可选调用 LLM 生成汇总报告。

运行方式：python exps/data-synthesis-workflow/opencode_demo/validate_env_demo.py [options]
"""

import argparse
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent

DEFAULT_ENV_DEMO_DIR = PROJECT_ROOT / "env_demo"

MCP_INITIALIZE_REQUEST = b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"validate","version":"1.0"}}}\n'

LLM_REPORT_PROMPT = """你是一名验证报告分析师。根据以下 env_demo 验证结果 JSON，生成一份中文汇总报告。

要求：
1. 统计通过数量与失败数量
2. 用表格列出失败的 env 名称及失败原因（steps 或 error 字段）
3. 对典型失败类型给出简要修复建议（如：缺少 pyproject.toml、依赖安装失败、MCP 未响应等）
4. 报告简洁清晰，便于开发者快速定位问题

验证结果 JSON：
```json
{results_json}
```

请直接输出报告内容，不要包含 JSON。"""


def get_env_dirs(env_demo_dir: Path) -> list[Path]:
    """获取 env_demo 下所有 env_ 开头的子目录"""
    if not env_demo_dir.exists():
        return []
    return sorted(
        p for p in env_demo_dir.iterdir()
        if p.is_dir() and p.name.startswith("env_")
    )


def check_structure(env_dir: Path) -> tuple[bool, Optional[str]]:
    """结构检查：mcp_server.py、tools/、pyproject.toml"""
    required = [
        ("mcp_server.py", env_dir / "mcp_server.py"),
        ("tools/", env_dir / "tools"),
        ("pyproject.toml", env_dir / "pyproject.toml"),
    ]
    for name, path in required:
        if not path.exists():
            return False, f"missing {name}"
    return True, None


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
        # 使用 uv run 以便使用 env 的 .venv 依赖
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

        # 解析 stdout 中的 JSON 行
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("Loaded tool:") or line.startswith("Stock Monitor") or line.startswith("---"):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "result" in obj:
                    caps = obj.get("result", {}).get("capabilities", {})
                    if "tools" in caps or "experimental" in caps:
                        return True, None
                    return True, None  # 有 result 即视为通过
                if isinstance(obj, dict) and "error" in obj:
                    return False, f"JSON-RPC error: {obj['error']}"
            except json.JSONDecodeError:
                continue

        err_msg = (stderr.decode("utf-8", errors="replace") or "").strip()[:300]
        return False, f"no valid JSON-RPC response in stdout" + (f"; stderr: {err_msg}" if err_msg else "")

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


def validate_one(env_dir: Path) -> dict:
    """验证单个 env，返回结果 dict"""
    env_name = env_dir.name
    steps = {}
    error = None

    # 1. 结构检查
    ok, err = check_structure(env_dir)
    steps["structure"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return {"ok": False, "steps": steps, "error": err}

    # 2. uv sync
    ok, err = run_uv_sync(env_dir)
    steps["uv_sync"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return {"ok": False, "steps": steps, "error": err}

    # 3. MCP initialize
    ok, err = run_mcp_initialize(env_dir)
    steps["mcp_initialize"] = "pass" if ok else f"fail: {err}"
    if not ok:
        return {"ok": False, "steps": steps, "error": err}

    return {"ok": True, "steps": steps, "error": None}


def call_llm_report(results: dict) -> str:
    """调用 LLM 生成汇总报告"""
    try:
        from dotenv import load_dotenv
        from openai import OpenAI
    except ImportError:
        return "Error: pip install python-dotenv openai for --llm-report"

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        return "Error: set OPENAI_API_KEY and OPENAI_MODEL in project .env for --llm-report"

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = LLM_REPORT_PROMPT.format(results_json=json.dumps(results, ensure_ascii=False, indent=2))

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"LLM call failed: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate all envs in env_demo: structure, uv sync, MCP initialize."
    )
    parser.add_argument(
        "--env-demo-dir",
        type=Path,
        default=DEFAULT_ENV_DEMO_DIR,
        help=f"env_demo root (default: {DEFAULT_ENV_DEMO_DIR})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max envs to validate (0 = all)",
    )
    parser.add_argument(
        "--llm-report",
        action="store_true",
        help="Call LLM to generate summary report after validation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write results JSON to file",
    )
    args = parser.parse_args()

    env_dirs = get_env_dirs(args.env_demo_dir.resolve())
    if not env_dirs:
        print(f"No env_* dirs found in {args.env_demo_dir}")
        return 1

    if args.limit:
        env_dirs = env_dirs[: args.limit]

    print("=" * 60)
    print("env_demo Validation")
    print("=" * 60)
    print(f"Env demo dir: {args.env_demo_dir}")
    print(f"Total envs: {len(env_dirs)}")
    print("=" * 60)

    results = {}
    for i, env_dir in enumerate(env_dirs):
        env_name = env_dir.name
        print(f"\n[{i+1}/{len(env_dirs)}] {env_name} ...", end=" ", flush=True)
        r = validate_one(env_dir)
        results[env_name] = r
        if r["ok"]:
            print("PASS")
        else:
            print("FAIL:", r.get("error", ""))

    # 输出 JSON
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nResults written to {args.output}")

    # LLM 报告
    if args.llm_report:
        print("\n" + "=" * 60)
        print("LLM Summary Report")
        print("=" * 60)
        report = call_llm_report(results)
        print(report)

    failed = [n for n, r in results.items() if not r["ok"]]
    print("\n" + "=" * 60)
    print(f"Done. Passed: {len(results) - len(failed)}, Failed: {len(failed)}")
    if failed:
        print("Failed:", ", ".join(failed))
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

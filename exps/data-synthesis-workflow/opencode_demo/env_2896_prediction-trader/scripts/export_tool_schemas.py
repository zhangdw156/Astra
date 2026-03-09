"""
将 tools/ 下各工具的 TOOL_SCHEMA 导出为 tools.jsonl（每行一个 JSON 对象）。
在 prediction-trader 目录下执行: python scripts/export_tool_schemas.py
"""
import importlib.util
import json
import sys
from pathlib import Path

# 项目根为 prediction-trader
ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
OUTPUT = ROOT / "tools.jsonl"


def main():
    schemas = []
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        # 避免导入时依赖未设置的环境等
        sys.modules[path.stem] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"跳过 {path.name}: {e}", file=sys.stderr)
            continue
        if not hasattr(mod, "TOOL_SCHEMA"):
            print(f"跳过 {path.name}: 无 TOOL_SCHEMA", file=sys.stderr)
            continue
        schemas.append(mod.TOOL_SCHEMA)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        for s in schemas:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"已写入 {len(schemas)} 个 schema -> {OUTPUT}")


if __name__ == "__main__":
    main()

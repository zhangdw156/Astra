"""
解析 tools.jsonl（轻量环境工具定义）。

纯函数，仅从文件读取并解析每行 JSON，返回工具 schema 列表。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_tools_from_jsonl(tools_jsonl: Path) -> List[Dict[str, Any]]:
    """
    解析 tools.jsonl（轻量环境）。

    每行一个 JSON 对象，需包含 "name" 字段；无效行跳过并打印警告。
    """
    tools: List[Dict[str, Any]] = []
    if not tools_jsonl.exists():
        return tools
    for line in tools_jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and "name" in obj:
                tools.append(obj)
        except json.JSONDecodeError:
            print(f"Invalid JSON in tools.jsonl line: {line[:120]}...")
    return tools

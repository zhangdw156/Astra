"""
Init Memory System Tool - 初始化记忆系统

初始化三级记忆系统，创建必要的目录和配置文件。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "init_memory_system",
    "description": "Initialize the three-tier memory management system. Creates necessary directories and config files for short-term (sliding window), medium-term (summaries), and long-term (vector store) memory. Use this first before adding any memories.",
    "inputSchema": {"type": "object", "properties": {}, "required": []},
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
CONFIG_FILE = MEMORY_DIR / "config.json"
SLIDING_WINDOW_FILE = MEMORY_DIR / "sliding-window.json"
SUMMARIES_DIR = MEMORY_DIR / "summaries"
VECTOR_STORE_DIR = MEMORY_DIR / "vector-store"

DEFAULT_CONFIG = {
    "memory": {
        "short_term": {"enabled": True, "window_size": 10, "max_tokens": 2000},
        "medium_term": {"enabled": True, "summary_threshold": 4000, "summary_model": "glm-4-flash"},
        "long_term": {"enabled": True, "backend": "chromadb", "top_k": 3, "min_relevance": 0.7},
    }
}


def ensure_dirs():
    """确保必要的目录存在"""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def execute() -> str:
    """初始化记忆系统"""
    ensure_dirs()

    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        result = f"Created config: {CONFIG_FILE}\n"
    else:
        result = f"Config already exists: {CONFIG_FILE}\n"

    if not SLIDING_WINDOW_FILE.exists():
        with open(SLIDING_WINDOW_FILE, "w") as f:
            json.dump(
                {"messages": [], "updated_at": datetime.now().isoformat()},
                f,
                indent=2,
                ensure_ascii=False,
            )
        result += f"Created short-term memory: {SLIDING_WINDOW_FILE}\n"
    else:
        result += f"Short-term memory already exists: {SLIDING_WINDOW_FILE}\n"

    result += f"\nMemory system initialized successfully!\n"
    result += f"  Short-term: {SLIDING_WINDOW_FILE}\n"
    result += f"  Medium-term: {SUMMARIES_DIR}\n"
    result += f"  Long-term: {VECTOR_STORE_DIR}\n"

    return result


if __name__ == "__main__":
    print(execute())

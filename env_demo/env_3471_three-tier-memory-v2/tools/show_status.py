"""
Show Status Tool - 显示记忆状态

显示三级记忆的当前状态。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "show_status",
    "description": "Show the current status of all three memory tiers: short-term (sliding window count), medium-term (number of summaries), and long-term (vector store count). Use this to understand memory usage.",
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
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    config_json = CONFIG_FILE
    if config_json.exists():
        with open(config_json, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def get_short_term_memory() -> list:
    if not SLIDING_WINDOW_FILE.exists():
        return []
    with open(SLIDING_WINDOW_FILE, "r") as f:
        data = json.load(f)
    return data.get("messages", [])


def get_medium_term_memory(days: int = 7) -> list:
    summaries = []
    cutoff = datetime.now().timestamp() - (days * 24 * 3600)

    for f in SUMMARIES_DIR.glob("*.json"):
        if f.stat().st_mtime > cutoff:
            with open(f, "r") as fp:
                data = json.load(fp)
                summaries.extend(data.get("summaries", []))

    return summaries


def execute() -> str:
    """显示记忆状态"""
    ensure_dirs()
    config = load_config()

    output = "## Three-Tier Memory Status\n\n"

    short_memories = get_short_term_memory()
    window_size = config["memory"]["short_term"]["window_size"]
    output += f"**Short-term**: {len(short_memories)}/{window_size} messages\n"
    if short_memories:
        latest = short_memories[-1]
        output += f"  Latest: {latest.get('content', '')[:50]}...\n"

    medium_memories = get_medium_term_memory()
    output += f"\n**Medium-term**: {len(medium_memories)} summaries (last 7 days)\n"

    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = client.get_collection("memory")
        long_count = collection.count()
        output += f"\n**Long-term**: {long_count} memories in vector store\n"
    except:
        output += f"\n**Long-term**: 0 memories\n"

    return output


if __name__ == "__main__":
    print(execute())

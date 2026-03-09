"""
Search Long-Term Memory Tool - 搜索长期记忆

使用向量相似度搜索长期记忆。
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

TOOL_SCHEMA = {
    "name": "search_long_term_memory",
    "description": "Search long-term memory using vector similarity. Uses semantic search to find relevant memories. Returns the most similar memories based on cosine distance.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant memories",
            },
            "top_k": {
                "type": "integer",
                "default": 3,
                "description": "Number of results to return",
            },
        },
        "required": ["query"],
    },
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
VECTOR_STORE_DIR = MEMORY_DIR / "vector-store"


def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def execute(query: str, top_k: int = 3) -> str:
    """搜索长期记忆"""
    ensure_dirs()

    try:
        import chromadb
    except ImportError:
        return "Error: chromadb not installed. Run: pip install chromadb"

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    try:
        collection = client.get_collection("memory")
    except:
        return "No long-term memories found. Add some memories first."

    results = collection.query(query_texts=[query], n_results=top_k)

    if not results or not results.get("documents") or not results["documents"][0]:
        return f"No memories found matching: {query}"

    output = f"## Search Results for: {query}\n\n"

    for i, doc in enumerate(results["documents"][0]):
        memory_id = results["ids"][0][i]
        distance = results["distances"][0][i] if "distances" in results else None
        similarity = f" (similarity: {1 - distance:.2f})" if distance else ""

        output += f"### {i + 1}. {memory_id}{similarity}\n"
        output += f"{doc}\n\n"

    return output


if __name__ == "__main__":
    print(execute("user preferences"))

"""
Add Long-Term Memory Tool - 添加长期记忆

长期记忆使用 ChromaDB 向量存储，支持语义检索。
"""

import os
import json
from datetime import datetime
from pathlib import Path

TOOL_SCHEMA = {
    "name": "add_long_term_memory",
    "description": "Add a long-term memory using vector store (ChromaDB). Long-term memory persists permanently and enables semantic search. Use this to store important information that should be retrievable across sessions.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The content to store in long-term memory",
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata to associate with the memory",
            },
        },
        "required": ["content"],
    },
}

WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", "/tmp/memory-workspace"))
MEMORY_DIR = WORKSPACE_DIR / "memory"
VECTOR_STORE_DIR = MEMORY_DIR / "vector-store"


def ensure_dirs():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)


def execute(content: str, metadata: dict = None) -> str:
    """添加长期记忆"""
    ensure_dirs()

    try:
        import chromadb
    except ImportError:
        return "Error: chromadb not installed. Run: pip install chromadb"

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))

    try:
        collection = client.get_collection("memory")
    except:
        collection = client.create_collection(
            "memory", metadata={"description": "Long-term memory store"}
        )

    memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    collection.add(
        documents=[content],
        ids=[memory_id],
        metadatas=[metadata or {"timestamp": datetime.now().isoformat()}],
    )

    return f"Added long-term memory: {memory_id}\nContent: {content[:80]}..."


if __name__ == "__main__":
    print(execute("User prefers dark mode interface"))

"""
Semantic Search Tool - Semantic search across documents in a pod

Performs semantic similarity search using embeddings. Requires sentence-transformers.
"""

import sqlite3
import json
from pathlib import Path

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "semantic_search",
    "description": "Perform semantic search across ingested documents in a pod. "
    "Uses embeddings to find semantically similar content. "
    "Requires sentence-transformers to be installed.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pod_name": {"type": "string", "description": "Name of the pod to search"},
            "query": {"type": "string", "description": "Natural language search query"},
            "top_k": {
                "type": "integer",
                "default": 5,
                "description": "Number of results to return",
            },
        },
        "required": ["pod_name", "query"],
    },
}

EMBEDDINGS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    pass


def generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2"):
    """Generate embedding for text."""
    if not EMBEDDINGS_AVAILABLE:
        return None

    try:
        model = SentenceTransformer(model_name)
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tobytes()
    except Exception as e:
        return None


def cosine_similarity(a: bytes, b: bytes) -> float:
    """Calculate cosine similarity between two embeddings."""
    import numpy as np

    a = np.frombuffer(a, dtype=np.float32)
    b = np.frombuffer(b, dtype=np.float32)

    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot / (norm_a * norm_b))


def execute(pod_name: str, query: str, top_k: int = 5) -> str:
    """Semantic search across documents."""
    if not EMBEDDINGS_AVAILABLE:
        return "Error: sentence-transformers not installed.\n\nInstall with: pip install sentence-transformers\n\nThis feature requires embeddings for semantic search."

    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found"

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT id, filename, chunks, embedding FROM documents WHERE embedding IS NOT NULL")
    rows = c.fetchall()

    if not rows:
        conn.close()
        return "No embedded documents found.\n\nRun ingest_folder first to ingest documents with embeddings."

    query_embedding = generate_embedding(query)
    if not query_embedding:
        conn.close()
        return "Error generating query embedding"

    results = []
    for row in rows:
        doc_id, filename, chunks_json, embedding = row
        if embedding:
            sim = cosine_similarity(query_embedding, embedding)
            chunks = json.loads(chunks_json) if chunks_json else []
            results.append((sim, filename, chunks[:3]))

    results.sort(reverse=True, key=lambda x: x[0])

    output = f"🔍 Semantic Search: '{query}'\n"
    output += f"Top {min(top_k, len(results))} results:\n\n"

    for i, (score, filename, chunks) in enumerate(results[:top_k], 1):
        output += f"**{i}. {filename}** (similarity: {score:.3f})\n"
        output += "-" * 40 + "\n"
        for chunk in chunks[:2]:
            output += f"   {chunk[:200]}...\n"
        output += "\n"

    conn.close()
    return output


if __name__ == "__main__":
    print(execute("test-pod", "machine learning"))

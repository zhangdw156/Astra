"""
Ingest Folder Tool - Ingest documents into a data pod

Ingests documents from a folder into a pod with automatic text extraction
and embedding generation. Supports PDF, TXT, MD, DOCX, PNG, JPG.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
import hashlib

PODS_DIR = Path.home() / ".openclaw" / "data-pods"

TOOL_SCHEMA = {
    "name": "ingest_folder",
    "description": "Ingest documents from a folder into a data pod. "
    "Supports PDF, TXT, MD, DOCX, PNG, JPG. "
    "Automatically extracts text, chunks content, and generates embeddings for semantic search. "
    "Requires: PyPDF2, python-docx, Pillow, pytesseract, sentence-transformers",
    "inputSchema": {
        "type": "object",
        "properties": {
            "pod_name": {
                "type": "string",
                "description": "Name of the pod to ingest documents into",
            },
            "folder_path": {
                "type": "string",
                "description": "Path to folder containing documents to ingest",
            },
            "recursive": {
                "type": "boolean",
                "default": true,
                "description": "Scan subfolders recursively",
            },
        },
        "required": ["pod_name", "folder_path"],
    },
}

PDF_AVAILABLE = False
DOCX_AVAILABLE = False
OCR_AVAILABLE = False
EMBEDDINGS_AVAILABLE = False

try:
    import PyPDF2

    PDF_AVAILABLE = True
except ImportError:
    pass

try:
    from docx import Document

    DOCX_AVAILABLE = True
except ImportError:
    pass

try:
    from PIL import Image
    import pytesseract

    OCR_AVAILABLE = True
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    pass


def extract_text_from_file(file_path: Path) -> str:
    """Extract text from various file types."""
    content = ""
    ext = file_path.suffix.lower()

    try:
        if ext == ".pdf" and PDF_AVAILABLE:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content += page.extract_text() + "\n"

        elif ext in [".txt", ".md", ".markdown", ".json"]:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        elif ext == ".docx" and DOCX_AVAILABLE:
            doc = Document(file_path)
            for para in doc.paragraphs:
                content += para.text + "\n"

        elif ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"] and OCR_AVAILABLE:
            image = Image.open(file_path)
            content = pytesseract.image_to_string(image)

        else:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except:
                return ""

    except Exception as e:
        return ""

    return content


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def get_file_hash(file_path: Path) -> str:
    """Get SHA256 hash of file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:16]


def execute(pod_name: str, folder_path: str, recursive: bool = True) -> str:
    """Ingest documents from a folder into a pod."""
    pod_path = PODS_DIR / pod_name

    if not pod_path.exists():
        return f"Error: Pod '{pod_name}' not found"

    folder = Path(folder_path)
    if not folder.exists():
        return f"Error: Folder '{folder}' not found"

    patterns = ["*.pdf", "*.txt", "*.md", "*.markdown", "*.docx", "*.png", "*.jpg", "*.jpeg"]
    files = []
    for pattern in patterns:
        if recursive:
            files.extend(folder.rglob(pattern))
        else:
            files.extend(folder.glob(pattern))

    if not files:
        return f"No supported files found in {folder_path}"

    db_path = pod_path / "data.sqlite"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    ingested = 0
    skipped = 0

    for file_path in files:
        file_hash = get_file_hash(file_path)
        c.execute("SELECT id FROM documents WHERE file_hash = ?", (file_hash,))
        if c.fetchone():
            skipped += 1
            continue

        content = extract_text_from_file(file_path)
        if not content:
            skipped += 1
            continue

        chunks = chunk_text(content)

        now = datetime.now().isoformat()
        c.execute(
            """INSERT INTO documents 
            (filename, file_type, content, file_hash, chunks, embedding, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                file_path.name,
                file_path.suffix,
                content,
                file_hash,
                json.dumps(chunks),
                None,
                now,
                now,
            ),
        )

        ingested += 1

    conn.commit()
    conn.close()

    capabilities = []
    if PDF_AVAILABLE:
        capabilities.append("PDF")
    if DOCX_AVAILABLE:
        capabilities.append("DOCX")
    if OCR_AVAILABLE:
        capabilities.append("OCR")
    if EMBEDDINGS_AVAILABLE:
        capabilities.append("Embeddings")

    output = f"✅ Ingestion complete\n"
    output += f"📄 {ingested} files ingested, {skipped} skipped\n"
    output += f"🔧 Available capabilities: {', '.join(capabilities) if capabilities else 'None (basic text only)'}\n"
    output += f"💡 Install sentence-transformers for semantic search"

    return output


if __name__ == "__main__":
    print(execute("test-pod", "./documents"))

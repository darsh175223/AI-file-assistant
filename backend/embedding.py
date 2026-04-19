"""
embedding.py
------------
Imported by main.py. Exposes embed_and_store(file_paths).

Pipeline: read file from disk → embed via Gemini → upsert to ChromaDB

Supports:
  - PDF files  → sent to Gemini as native base64 (no text extraction needed)
  - Text files → sent as plain string with task instruction prefix

Config lives in env/.env:
  GEMINI_API_KEY
  CHROMA_HOST       (default: localhost)
  CHROMA_PORT       (default: 8000)
  CHROMA_COLLECTION (default: file_embeddings)

NOTE: gemini-embedding-2-preview does not support the task_type parameter.
Task intent is passed as a plain-text instruction prefix instead.
"""

import os
import hashlib
import base64
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
import chromadb

# ── Config ────────────────────────────────────────────────────────────────────

env_path = Path(__file__).parent / "env" / ".env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
CHROMA_HOST       = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT       = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "file_embeddings")

EMBEDDING_MODEL      = "gemini-embedding-2-preview"
EMBEDDING_DIM        = 768        # 768 | 1536 | 3072
DOCUMENT_TASK_PREFIX = "task: retrieval document\n\n"

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found. Set it in env/.env")


# ── Helpers ───────────────────────────────────────────────────────────────────

def file_id(path: str) -> str:
    """Stable unique ID derived from the file's absolute path."""
    return hashlib.md5(str(Path(path).resolve()).encode()).hexdigest()


def is_pdf(path: str) -> bool:
    return Path(path).suffix.lower() == ".pdf"


def build_gemini_content(path: str) -> tuple[list, str]:
    """
    Read a file and build the Gemini content payload.

    Returns:
        (content, document_text) where:
          content       → passed to embed_content()
          document_text → stored in ChromaDB's document field
    """
    file_bytes = Path(path).read_bytes()

    if is_pdf(path):
        content = [
            types.Part(
                inline_data=types.Blob(
                    mime_type="application/pdf",
                    data=base64.b64encode(file_bytes).decode("utf-8"),
                )
            )
        ]
        document_text = f"[PDF: {Path(path).name}]"
    else:
        text = file_bytes.decode("utf-8", errors="replace")
        content       = [DOCUMENT_TASK_PREFIX + text]
        document_text = text

    return content, document_text


# ── Embedding ─────────────────────────────────────────────────────────────────

def get_embeddings(files: list[dict]) -> list[dict]:
    """
    Embed each file via Gemini. Files are processed individually because
    PDFs and text require different content formats and can't be batched together.

    Each item in `files` must have: {path, document_text, content}
    Adds an `embedding` key to each item.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)

    for file in files:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=file["content"],
            config=types.EmbedContentConfig(
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        file["embedding"] = result.embeddings[0].values

    return files


# ── ChromaDB ──────────────────────────────────────────────────────────────────

def get_chroma_collection() -> chromadb.Collection:
    """Connect to ChromaDB and return (or create) the target collection."""
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    chroma.heartbeat()
    return chroma.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_to_chroma(collection: chromadb.Collection, files: list[dict]) -> None:
    """Upsert embeddings, document text, and metadata into ChromaDB."""
    collection.upsert(
        ids        = [file_id(f["path"])       for f in files],
        embeddings = [f["embedding"]           for f in files],
        documents  = [f["document_text"]       for f in files],
        metadatas  = [
            {
                "filename":   Path(f["path"]).name,
                "source":     str(Path(f["path"]).resolve()),
                "filetype":   "pdf" if is_pdf(f["path"]) else "text",
            }
            for f in files
        ],
    )


# ── Public API ────────────────────────────────────────────────────────────────

def embed_and_store(file_paths: list[str]) -> dict:
    """
    Full pipeline: read from disk → embed → store in ChromaDB.
    Handles both PDF and plain text files.

    Args:
        file_paths: List of absolute paths to files on disk.

    Returns:
        {"stored": int, "skipped": list[str]}
    """
    files, skipped = [], []

    for path in file_paths:
        try:
            content, document_text = build_gemini_content(path)
            files.append({
                "path":          path,
                "content":       content,
                "document_text": document_text,
            })
        except Exception as e:
            print(f"[embedding] Skipped '{path}': {e}")
            skipped.append(path)

    if files:
        files      = get_embeddings(files)
        collection = get_chroma_collection()
        upsert_to_chroma(collection, files)

    return {"stored": len(files), "skipped": skipped}
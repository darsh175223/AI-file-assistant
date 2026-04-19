"""
search.py
---------
Imported by main.py. Exposes search_similar(query_text, n_results).

Embeds the query via gemini-embedding-2-preview and returns the most
similar documents from ChromaDB.

Config lives in env/.env:
  GEMINI_API_KEY
  CHROMA_HOST       (default: localhost)
  CHROMA_PORT       (default: 8000)
  CHROMA_COLLECTION (default: file_embeddings)

NOTE: gemini-embedding-2-preview does not support the task_type parameter.
The query task is passed as a plain-text instruction prefix instead.
"""

import os
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

EMBEDDING_MODEL   = "gemini-embedding-2-preview"
EMBEDDING_DIM     = 768
QUERY_TASK_PREFIX = "task: retrieval query\n\n"


# ── Public API ────────────────────────────────────────────────────────────────

def search_similar(query_text: str, n_results: int = 3) -> list[dict]:
    """
    Embed a query string and return the most similar documents from ChromaDB.

    Args:
        query_text: The search query.
        n_results:  Number of top results to return (default 3).

    Returns:
        List of dicts:
          - filename : original file name
          - source   : absolute path on disk at time of embedding
          - filetype : 'pdf' or 'text'
          - distance : cosine distance — lower means more similar
          - text     : stored document text (or '[PDF: name.pdf]' for PDFs)

    Raises:
        EnvironmentError : GEMINI_API_KEY missing
        Exception        : collection doesn't exist or is empty
    """
    if not GEMINI_API_KEY:
        raise EnvironmentError("GEMINI_API_KEY not found in env/.env")

    # 1. Embed the query with the QUERY task prefix
    gemini = genai.Client(api_key=GEMINI_API_KEY)
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=QUERY_TASK_PREFIX + query_text,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    query_vector = result.embeddings[0].values

    # 2. Connect to ChromaDB
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    try:
        collection = chroma.get_collection(CHROMA_COLLECTION)
    except Exception:
        raise Exception(
            f"Collection '{CHROMA_COLLECTION}' does not exist yet. "
            "Embed some files first via POST /embed-files."
        )

    count = collection.count()
    if count == 0:
        raise Exception(
            f"Collection '{CHROMA_COLLECTION}' is empty. "
            "Embed some files first via POST /embed-files."
        )

    # 3. Query — can't request more results than docs stored
    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    # 4. Shape and return results
    return [
        {
            "filename": meta.get("filename"),
            "source":   meta.get("source"),
            "filetype": meta.get("filetype", "unknown"),
            "distance": round(dist, 6),
            "text":     doc,
        }
        for doc, meta, dist in zip(
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        )
    ]
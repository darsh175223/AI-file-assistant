"""
Gemini Embedding Script → ChromaDB
------------------------------------
Reads a list of file paths, generates embeddings via gemini-embedding-001,
and upserts the vectors into a running ChromaDB HTTP server.
 
Setup:
  1. Create env/.env with:
       GEMINI_API_KEY=your_gemini_key_here
       CHROMA_HOST=localhost
       CHROMA_PORT=8000
       CHROMA_COLLECTION=file_embeddings
 
  2. Install dependencies:
       pip install google-genai chromadb python-dotenv
 
  3. Start ChromaDB server (pick one):
       chroma run --host 0.0.0.0 --port 8000 --path ./chroma_data
       docker run -d -p 8000:8000 -v $(pwd)/chroma_data:/chroma/chroma chromadb/chroma:latest
"""
 
import os
import sys
import hashlib
from pathlib import Path
 
from dotenv import load_dotenv
from google import genai
from google.genai import types
import chromadb
 
 
# ── Config ───────────────────────────────────────────────────────────────────
 
env_path = Path(__file__).parent / "env" / ".env"
load_dotenv(dotenv_path=env_path)
 
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
CHROMA_HOST       = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT       = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "file_embeddings")
 
EMBEDDING_MODEL   = "gemini-embedding-001"
EMBEDDING_DIM     = 768   # 768 | 1536 | 3072
EMBEDDING_TASK    = "RETRIEVAL_DOCUMENT"
 
if not GEMINI_API_KEY:
    sys.exit("ERROR: GEMINI_API_KEY not found in env/.env")
 
 
# ── Helpers ──────────────────────────────────────────────────────────────────
 
def file_id(path: str) -> str:
    """Stable, unique ID for a file based on its absolute path."""
    return hashlib.md5(str(Path(path).resolve()).encode()).hexdigest()
 
 
def load_files(file_paths: list[str]) -> list[dict]:
    """Read files from disk. Returns list of {path, text} dicts."""
    loaded = []
    for path in file_paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
            loaded.append({"path": path, "text": text})
            print(f"  ✓ Loaded : {path} ({len(text):,} chars)")
        except Exception as e:
            print(f"  ✗ Skipped: {path} — {e}")
    return loaded
 
 
# ── Embedding ─────────────────────────────────────────────────────────────────
 
def get_embeddings(files: list[dict]) -> list[dict]:
    """
    Call Gemini embedding API for all file texts in a single batched request.
    Returns the input list with an 'embedding' key added to each item.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    texts  = [f["text"] for f in files]
 
    print(f"\nCalling {EMBEDDING_MODEL} for {len(texts)} file(s)...")
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=EMBEDDING_TASK,
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
 
    for file, emb_obj in zip(files, result.embeddings):
        file["embedding"] = emb_obj.values   # list[float]
 
    print(f"  ✓ Received {len(result.embeddings)} embedding(s), dim={EMBEDDING_DIM}")
    return files
 
 
# ── ChromaDB ──────────────────────────────────────────────────────────────────
 
def get_chroma_collection() -> chromadb.Collection:
    """Connect to the remote ChromaDB server and return (or create) the collection."""
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
 
    # Sanity-check the connection
    chroma.heartbeat()
    print(f"\nConnected to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}")
 
    # get_or_create so the script is safe to run multiple times
    collection = chroma.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},   # cosine distance for semantic search
    )
    print(f"  Collection : '{CHROMA_COLLECTION}' "
          f"(existing docs: {collection.count()})")
    return collection
 
 
def upsert_to_chroma(collection: chromadb.Collection, files: list[dict]) -> None:
    """
    Upsert embeddings + metadata into ChromaDB.
    Uses upsert so re-running the script updates existing docs rather than erroring.
    """
    ids        = [file_id(f["path"])      for f in files]
    embeddings = [f["embedding"]          for f in files]
    documents  = [f["text"]               for f in files]
    metadatas  = [
        {
            "source":     str(Path(f["path"]).resolve()),
            "filename":   Path(f["path"]).name,
            "char_count": len(f["text"]),
        }
        for f in files
    ]
 
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    print(f"\n  ✓ Upserted {len(ids)} document(s) into '{CHROMA_COLLECTION}'")
    print(f"  Collection now contains {collection.count()} total doc(s)")
 
 
# ── Pipeline ──────────────────────────────────────────────────────────────────
 
def embed_and_store(file_paths: list[str]) -> None:
    """Full pipeline: load → embed → store."""
    print("=== Step 1: Load files ===")
    files = load_files(file_paths)
    if not files:
        print("Nothing to process.")
        return
 
    print("\n=== Step 2: Generate embeddings ===")
    files = get_embeddings(files)
 
    print("\n=== Step 3: Store in ChromaDB ===")
    collection = get_chroma_collection()
    upsert_to_chroma(collection, files)
 
    print("\n✅ Done.")
 
 
# ── Optional: query helper ────────────────────────────────────────────────────
 
def query_similar(query_text: str, n_results: int = 3) -> None:
    """
    Convenience function: embed a query string and find the most similar
    stored documents. Run separately after embed_and_store().
    """
    gemini = genai.Client(api_key=GEMINI_API_KEY)
    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query_text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",       # use QUERY task for search queries
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    query_vector = result.embeddings[0].values
 
    chroma     = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = chroma.get_collection(CHROMA_COLLECTION)
    results    = collection.query(
        query_embeddings=[query_vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )
 
    print(f"\n=== Top {n_results} results for: '{query_text}' ===")
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        print(f"\n[{i+1}] {meta['filename']}  (distance: {dist:.4f})")
        print(f"     {doc[:200]}{'...' if len(doc) > 200 else ''}")
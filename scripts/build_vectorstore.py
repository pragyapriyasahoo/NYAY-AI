"""
Embed all chunks and store them in a local ChromaDB vector store.
Run after chunk_data.py has produced data/processed/chunks.json.
Re-running rebuilds the collection from scratch (no duplicates).

Uses COSINE distance and normalized embeddings, so distance cutoffs
in rag_query.py and eval_retrieval.py are meaningful.

First run downloads the embedding model (~1GB, then cached).

Usage:
    python scripts/build_vectorstore.py
"""

import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent.parent
CHUNKS_FILE = ROOT / "data" / "processed" / "chunks.json"
VECTORSTORE_DIR = ROOT / "vectorstore"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
COLLECTION_NAME = "nyay_ai_legal_chunks"


def main():
    if not CHUNKS_FILE.exists():
        print(f"No chunks found at {CHUNKS_FILE}. Run chunk_data.py first.")
        return

    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks.")

    print(f"Loading embedding model: {EMBED_MODEL_NAME} ...")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    # e5 models expect a "passage: " prefix for documents being stored
    texts = [f"passage: {c['text']}" for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [
        {
            "source": c["source"],
            "section": str(c.get("section") or ""),
            "title": c.get("title") or "",
        }
        for c in chunks
    ]

    print("Generating embeddings (a few minutes on CPU)...")
    embeddings = model.encode(
        texts, show_progress_bar=True, batch_size=16, normalize_embeddings=True
    ).tolist()

    print("Storing in ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],  # original text, without "passage:"
        metadatas=metadatas,
    )

    print(f"\nDone. {len(chunks)} chunks embedded and stored in {VECTORSTORE_DIR}")


if __name__ == "__main__":
    main()
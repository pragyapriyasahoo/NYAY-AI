"""
Phase 3: Embed all chunks and store them in a local ChromaDB vector store.
Run this after chunk_data.py has produced data/processed/chunks.json.

First run will download the embedding model (~1GB, one-time, then cached).

Usage:
    python scripts/build_vectorstore.py
"""

import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path(__file__).parent.parent / "data" / "processed" / "chunks.json"
VECTORSTORE_DIR = Path(__file__).parent.parent / "vectorstore"

EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
COLLECTION_NAME = "nyay_ai_legal_chunks"


def main():
    if not CHUNKS_FILE.exists():
        print(f"No chunks found at {CHUNKS_FILE}. Run chunk_data.py first.")
        return

    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks.")

    print(f"Loading embedding model: {EMBED_MODEL_NAME} (first run downloads it)...")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    # e5 models expect a "passage: " prefix for documents being stored
    texts = [f"passage: {c['text']}" for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [{"source": c["source"]} for c in chunks]

    print("Generating embeddings (this may take a few minutes on CPU)...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=16).tolist()

    print("Storing in ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    # Fresh collection each run so re-running this script doesn't duplicate/stale data
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],   # store original text, not the "passage:" version
        metadatas=metadatas,
    )

    print(f"\nDone. {len(chunks)} chunks embedded and stored in {VECTORSTORE_DIR}")
    print(f"Collection name: {COLLECTION_NAME}")


if __name__ == "__main__":
    main()

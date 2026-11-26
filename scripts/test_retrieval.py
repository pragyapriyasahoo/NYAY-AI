"""
Quick sanity check: query the vectorstore and see what comes back.
Run this after build_vectorstore.py to confirm retrieval is working
before connecting the LLM.

Usage:
    python scripts/test_retrieval.py "landlord deposit nahi de raha"
"""

import sys
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

VECTORSTORE_DIR = Path(__file__).parent.parent / "vectorstore"
EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
COLLECTION_NAME = "nyay_ai_legal_chunks"


def main():
    query = " ".join(sys.argv[1:]) or "landlord deposit nahi de raha"
    print(f"Query: {query}\n")

    model = SentenceTransformer(EMBED_MODEL_NAME)
    # e5 models expect a "query: " prefix for search queries
    query_embedding = model.encode([f"query: {query}"]).tolist()

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    results = collection.query(query_embeddings=query_embedding, n_results=3)

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    )):
        print(f"--- Result {i+1} (source: {meta['source']}, distance: {dist:.3f}) ---")
        print(doc[:300])
        print()


if __name__ == "__main__":
    main()

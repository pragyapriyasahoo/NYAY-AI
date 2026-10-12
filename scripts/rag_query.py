"""
Phase 4: Full RAG pipeline — retrieve relevant chunks, then ask a local
Ollama model to answer in Hindi, grounded only in those chunks.

Make sure Ollama is running in the background (it usually auto-starts
after install; if not, run `ollama serve` in a separate terminal).

Usage:
    python scripts/rag_query.py "landlord deposit nahi de raha"
    python scripts/rag_query.py "product defective hai refund kaise le" --model llama3
"""

import sys
import argparse
import requests
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

VECTORSTORE_DIR = Path(__file__).parent.parent / "vectorstore"
EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
COLLECTION_NAME = "nyay_ai_legal_chunks"
OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """Aap ek legal-jaankari sahayak hain jo Bharat ke Consumer Protection Act aur Tamil Nadu Tenancy Act ke baare mein Hindi mein jawab dete hain.

SAKHT NIYAM:
1. Neeche diye gaye "Context" ke legal principles ko user ke sawal se jodo aur samjhao — context mein jo likha hai wahi jaankari ka aadhar hai, lekin usko user ki situation par apply karke explain karna tumhara kaam hai. Naye facts, sections, ya numbers mat banao jo context mein nahi hain.
2. Agar context ka koi bhi hissa user ke sawal se related nahi hai (bilkul alag topic), tabhi bolo: "Mujhe iske baare mein jaankari nahi mili."
3. Jawab simple, saral Hindi mein do — legal jargon avoid karo.
4. Jawab ke end mein hamesha likho: "Yeh legal advice nahi hai, sirf jaankari hai. Sahi salah ke liye vakil ya Legal Aid Clinic se sampark karein."
"""


def retrieve_chunks(query: str, k: int = 5):
    model = SentenceTransformer(EMBED_MODEL_NAME)
    query_embedding = model.encode([f"query: {query}"]).tolist()

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "source": meta["source"]})
    return chunks


def build_prompt(query: str, chunks: list) -> str:
    context = "\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nUser ka sawal: {query}\n\nJawab:"


def ask_ollama(prompt: str, model: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["response"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="+", help="User's question")
    parser.add_argument("--model", default="gemma3:4b", help="Ollama model to use")
    args = parser.parse_args()

    query = " ".join(args.query)
    print(f"Query: {query}\n")

    print("Retrieving relevant chunks...")
    chunks = retrieve_chunks(query)
    for c in chunks:
        print(f"  - matched: {c['source']}")

    prompt = build_prompt(query, chunks)

    print(f"\nAsking {args.model}...\n")
    try:
        answer = ask_ollama(prompt, args.model)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not reach Ollama. Is it running? Try `ollama serve` in another terminal.")
        sys.exit(1)

    print("=" * 50)
    print(answer)
    print("=" * 50)


if __name__ == "__main__":
    main()

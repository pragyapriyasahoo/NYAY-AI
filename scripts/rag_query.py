"""
Nyay AI - RAG query pipeline (final build).

Flow:
  1. LLM rewrites Hinglish/Hindi query into English legal keywords (retrieval only)
  2. ChromaDB returns candidate chunks (cosine)
  3. Cross-encoder reranks them
  4. Top score below MIN_SCORE -> not_found
  5. Top distinct sections are shown as verbatim Act text (section's first chunk = main rule)

The LLM never writes the answer.

Usage:
    python scripts/rag_query.py "ghar khali karne ko bola, bina notice ke nahi nikal sakte"
    python scripts/rag_query.py "..." --no-rewrite
"""
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"

import re
import json
import argparse
import unicodedata
from pathlib import Path

import requests
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

ROOT = Path(__file__).resolve().parent.parent
VECTORSTORE_DIR = ROOT / "vectorstore"
EMBED_MODEL_NAME = "intfloat/multilingual-e5-base"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
COLLECTION_NAME = "nyay_ai_legal_chunks"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

DEFAULT_MODEL = "gemma3:4b"
RETRIEVE_K = 10          # candidates from ChromaDB before reranking
MAX_OPTIONS = 3          # distinct sections shown
MIN_SCORE = 1.5          # from test_guard: in-scope >= 4.28, out-of-scope <= 2.12

NOT_FOUND = "Mujhe iske baare mein jaankari nahi mili."
DISCLAIMER = ("Yeh legal advice nahi hai, sirf jaankari hai. "
              "Sahi salah ke liye vakil ya Legal Aid Clinic se sampark karein.")

REWRITE_PROMPT = """Convert the question (Hindi or Hinglish) about Indian tenancy or consumer law into English search keywords.

Rules:
- Keep the key nouns of the question in English (deposit, rent, electricity, water, receipt, repair, refund, complaint, etc.).
- Where they fit, use the official legal terms: security deposit, rent, receipt for rent, repairs and maintenance, essential supply or service, cutting off or withholding, repossession of the premises, recovery of possession, notice of giving up possession, entry with notice, advance rent, revision of rent, tenancy agreement, defective goods, deficiency in service, unfair trade practice, consumer complaint.
- Do not add generic words like "consumer protection", "rights", "law" or "India" unless the question is about a product or service.
- Do not answer the question. Do not include section numbers.

Return ONLY JSON: {{"keywords": "<8 to 15 English words>"}}

Question: {q}
"""

ZERO_WIDTH = re.compile(r"[\u200b-\u200d\ufeff]")
_EMBEDDER = None
_COLLECTION = None
_RERANKER = None


def normalize(text: str) -> str:
    return ZERO_WIDTH.sub("", unicodedata.normalize("NFC", text))


def rewrite_query(query: str, model: str = DEFAULT_MODEL) -> str:
    """LLM -> English keywords. Returns '' on any failure (pipeline continues)."""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": model,
                  "prompt": REWRITE_PROMPT.format(q=query),
                  "stream": False,
                  "format": "json",
                  "options": {"temperature": 0, "num_predict": 60}},
            timeout=60,
        )
        r.raise_for_status()
        kw = json.loads(r.json()["response"]).get("keywords", "")
        return str(kw).strip()[:300]
    except Exception:
        return ""


def _load():
    global _EMBEDDER, _COLLECTION, _RERANKER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer(EMBED_MODEL_NAME)
    if _COLLECTION is None:
        _COLLECTION = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR)).get_collection(COLLECTION_NAME)
    if _RERANKER is None:
        _RERANKER = CrossEncoder(RERANK_MODEL_NAME)
    return _EMBEDDER, _COLLECTION, _RERANKER


def retrieve(query: str, use_rewrite: bool = True, model: str = DEFAULT_MODEL):
    keywords = rewrite_query(query, model) if use_rewrite else ""
    expanded = f"{normalize(query)} {keywords}".strip()
    embedder, collection, _ = _load()
    emb = embedder.encode([f"query: {expanded}"], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=emb, n_results=RETRIEVE_K)
    chunks = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        chunks.append({"text": doc,
                       "source": meta.get("source", ""),
                       "section": meta.get("section", ""),
                       "title": meta.get("title", ""),
                       "distance": dist})
    return chunks, keywords


def rerank(query_en: str, chunks: list) -> list:
    if not chunks:
        return chunks
    _, _, reranker = _load()
    scores = reranker.predict([(query_en, c["text"]) for c in chunks])
    for c, s in zip(chunks, scores):
        c["rerank"] = float(s)
    return sorted(chunks, key=lambda c: c["rerank"], reverse=True)


def section_head(c: dict) -> str:
    """First chunk of the section (contains the main rule). Falls back to the chunk itself."""
    if not c["section"]:
        return c["text"]
    try:
        _, collection, _ = _load()
        got = collection.get(ids=[f"{c['source']}_s{c['section']}_0"])
        if got["documents"]:
            return got["documents"][0]
    except Exception:
        pass
    return c["text"]


def label(c: dict) -> str:
    if c["section"]:
        return f"{c['source'][:45]}, Section {c['section']} ({c['title']})"
    return c["source"][:45]


def answer_query(query: str, model: str = DEFAULT_MODEL,
                 min_score: float = MIN_SCORE, use_rewrite: bool = True) -> dict:
    chunks, keywords = retrieve(query, use_rewrite, model)
    res = {"chunks": chunks, "keywords": keywords, "mode": None,
           "chosen": None, "options": []}
    if not chunks:
        res["mode"] = "not_found"
        return res

    ranked = rerank(keywords or query, chunks)
    if ranked[0]["rerank"] < min_score:
        res["mode"] = "not_found"
        return res

    seen, options = set(), []
    for c in ranked:
        if c["rerank"] < min_score:
            break
        key = (c["source"], c["section"])
        if key in seen:
            continue
        seen.add(key)
        options.append(c)
        if len(options) == MAX_OPTIONS:
            break

    res.update(mode="retrieved", chosen=options[0], options=options)
    return res

CHAT_PROMPT = """Tum ek dost jaise sahayak ho jo Indian kiraye (tenant) aur consumer rights aam logon ko samjhate ho.
Neeche diye gaye kanoon ke text ke aadhar par, sawaal ka seedha aur saral jawab Hinglish (Roman script) mein do.

Jawab ka tarika:
- Pehle ek line mein seedha jawab do (haan, nahi, ya kitna, kya haq hai).
- Phir 1 se 2 line mein batao ki kya karna chahiye, jaise kisse shikayat karni hai.
- Kul 3 se 5 chhoti line. Friendly tone, lekin legal jargon nahi.
- Sirf is kanoon ke text ki baat karo. Bahar ki jaankari mat do.
- Koi naya number, din, mahina, rupaya ya section number mat likho jo text mein na ho.
- Agar text sawaal ka jawab nahi deta, to sirf likho: NOT_ANSWERED

Kanoon ka text:
\"\"\"{law}\"\"\"

Sawaal: {q}
Jawab:"""

_NUM = re.compile(r"\d+")


def warm_llm(model: str = DEFAULT_MODEL):
    """Load the model into memory once, so the first real question is not slow."""
    try:
        requests.post(OLLAMA_URL,
                      json={"model": model, "prompt": "hi", "stream": False,
                            "keep_alive": "30m", "options": {"num_predict": 1}},
                      timeout=300)
    except Exception:
        pass


def chat_answer(query: str, law_text: str, model: str = DEFAULT_MODEL) -> str:
    """Hinglish chat answer grounded in the law text. Returns '' if unsafe or failed."""
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": model,
                  "prompt": CHAT_PROMPT.format(law=law_text[:1500], q=query),
                  "stream": False,
                  "keep_alive": "30m",
                  "options": {"temperature": 0.2, "num_predict": 200, "repeat_penalty": 1.1}},
            timeout=180,
        )
        r.raise_for_status()
        text = r.json()["response"].strip()
    except Exception:
        return ""

    if not text or "NOT_ANSWERED" in text:
        return ""

    # Safety: every number in the answer must come from the law text or the question
    allowed = set(_NUM.findall(law_text)) | set(_NUM.findall(query))
    if any(n not in allowed for n in _NUM.findall(text)):
        return ""
    return text

def show(res: dict):
    if res["mode"] == "not_found":
        print(NOT_FOUND)
    else:
        print(f"Sahi section in mein se ho sakta hai (top {len(res['options'])}):\n")
        for i, c in enumerate(res["options"], 1):
            print(f"--- Option {i}: {label(c)}  (score={c['rerank']:.2f})")
            print(" ".join(section_head(c).split())[:600])
            print()
        print(DISCLAIMER)
    print("=" * 50)
    print(f"mode={res['mode']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--min-score", type=float, default=MIN_SCORE)
    ap.add_argument("--no-rewrite", action="store_true")
    args = ap.parse_args()

    query = " ".join(args.query)
    print(f"Query: {query}")
    res = answer_query(query, args.model, args.min_score, use_rewrite=not args.no_rewrite)
    if res["keywords"]:
        print(f"(keywords: {res['keywords']})")
    show(res)


if __name__ == "__main__":
    main()
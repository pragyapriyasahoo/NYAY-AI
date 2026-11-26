# ⚖️ Nyay AI

> **Tenancy and consumer law, explained in your language.**
> A local, offline RAG assistant that finds the right sections of Indian tenancy and consumer law and shows them as verbatim source text.

![status](https://img.shields.io/badge/status-in%20development-orange)
![python](https://img.shields.io/badge/python-3.11-blue)
![license](https://img.shields.io/badge/license-TBD-lightgrey)

---

## 🧩 Problem

Ordinary people often need to understand their rights on issues like security deposits, electricity being cut off, or being asked to vacate without notice. But:

- Legal text is written in formal English with heavy jargon.
- Finding the exact section that applies to a situation is hard.
- Online answers are often outdated, generic, or from the wrong state.
- Consulting a lawyer can be expensive and slow.

## 💡 Solution

Nyay AI turns a user's Hinglish or Hindi question into English legal search queries, finds the matching Act sections, and shows them as **verbatim source text**.

The principle is simple: **show the actual law before generating any answer.**

- 🔍 Searches for sections relevant to the question
- 📜 Every result is based on the Act's own text
- 🚫 If the law does not cover the question, it says so ("information not found")
- ⚠️ Every result comes with a disclaimer: this is not legal advice

## 🎯 Who this repo serves

| Who | Why |
|---|---|
| Tenants and landlords | To understand their rights and duties |
| Consumers | First-level information on refunds, defective goods, and complaints |
| Legal Aid volunteers | To reach the right section quickly |
| Developers and researchers | A reference for a Hindi-first, local, low-resource legal RAG system |

**Scope:** Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act, 2017, and the Consumer Protection Act, 2019. This is general information, not legal advice.

---

## 🏗️ Architecture

```
            ┌──────────────────────────────┐
            │   Source PDFs (data/raw)     │
            └──────────────┬───────────────┘
                           │ pdfplumber + cleaning
                           ▼
            ┌──────────────────────────────┐
            │  TOC-based section chunker   │
            │  (chunk_data.py)             │
            └──────────────┬───────────────┘
                           │ chunks.json (section id, title)
                           ▼
            ┌──────────────────────────────┐
            │  Embeddings (e5-base, cosine)│
            │  → ChromaDB vector store     │
            └──────────────┬───────────────┘
                           │
  User query ──────────────┤
  (Hinglish / Hindi)       │
        │                  │
        ▼                  ▼
  ┌─────────────┐   ┌──────────────────┐
  │ LLM (Ollama)│   │ Multi-query      │
  │ → English   │──▶│ retrieval + pool │
  │ search qs   │   └────────┬─────────┘
  └─────────────┘            │ top candidates
                             ▼
                  ┌──────────────────────┐
                  │ Cross-encoder rerank │
                  │ + score gate         │
                  └────────┬─────────────┘
                           │
            ┌──────────────┴──────────────┐
            ▼                             ▼
     score ≥ gate                 score < gate
     top distinct sections        "information not found"
     (verbatim Act text)
            │
            ▼
     Streamlit UI (app.py)
```

### Components

| Layer | File | Role |
|---|---|---|
| Extraction | `scripts/extract_pdf.py` | PDF to text, gazette and footnote cleaning |
| Chunking | `scripts/chunk_data.py` | Section-wise chunks with header `Section N. Title.` |
| Indexing | `scripts/build_vectorstore.py` | e5 embeddings, ChromaDB (cosine) |
| Retrieval | `scripts/rag_query.py` | Query generation, pooled search, reranking, gate |
| Evaluation | `scripts/eval_retrieval.py`, `scripts/test_guard.py` | Recall/MRR, out-of-scope checks |
| UI | `app.py` | Streamlit chat |

---

## 🔧 System design

**Design principles**

1. **Grounded by default.** Every result is traceable to Act text.
2. **Fail closed.** Below the score gate, the system answers "not found".
3. **No hardcoded legal rules.** No per-question rules or keyword maps.
4. **Local and cheap.** Ollama and open models that run on CPU.
5. **Measure before tuning.** Evaluation set first, tuning after.

**Current flow**

| Step | What happens | Model / tool |
|---|---|---|
| 1 | Turn the Hinglish question into English search queries | Ollama (gemma3:4b) |
| 2 | Search ChromaDB with the original and English queries, pool results | multilingual-e5-base |
| 3 | Score pooled passages against the English queries | ms-marco-MiniLM-L-6-v2 |
| 4 | Apply score gate, keep top 3 distinct sections | threshold (calibration pending) |
| 5 | Show verbatim section text | ChromaDB metadata |

**Planned** (see `docs/`)

- Devanagari grounded answers with citation, number, language and faithfulness checks
- Fallback ladder: verified answer → unverified section view → not found
- Evaluation with dev/test split (`data/eval/gold.json`)
- FastAPI service (`/clauses`, `/answer`, `/health`) with Streamlit as a thin client
- Text PDF upload, then OCR for scanned notices
- Docker and Ollama compose for deployment

## ⚠️ Limitations

- Retrieval is not yet calibrated. Sometimes the wrong section ranks first.
- Answers are currently in Hinglish or English. Devanagari grounded answers are planned.
- PDF extraction can leave some text noise.
- Evaluation numbers are not published yet.

## ⚖️ Disclaimer

This tool provides general legal information. It is not a substitute for a lawyer's advice. Before taking any legal action, contact a Legal Aid Clinic or a qualified lawyer.

## 📄 License

TBD

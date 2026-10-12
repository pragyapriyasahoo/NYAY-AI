# Nyay AI: Legal Rights in Simple Hindi

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Architecture](https://img.shields.io/badge/Architecture-RAG-orange)
![LLM](https://img.shields.io/badge/LLM-Ollama%20local-black)
![Vector DB](https://img.shields.io/badge/Vector%20DB-ChromaDB-green)
![Language](https://img.shields.io/badge/Language-Hindi-ff9933)
![Paid APIs](https://img.shields.io/badge/Paid%20APIs-None-brightgreen)
![Status](https://img.shields.io/badge/Status-In%20Progress-yellow)

A fully local, Hindi-first Retrieval-Augmented Generation (RAG) assistant that helps common Indians understand their consumer and tenant rights, grounded in the actual text of the law.

Crores of Indians never use their legal rights because the law is written in complex English legalese and lawyers are expensive. Nyay AI lets a user describe a problem in plain Hindi (for example, "landlord deposit nahi de raha") and get a simple explanation based on the relevant Act.

---

## Why Nyay AI is different (USPs)

- **Hindi-first, common-man focus.** Most legal-tech in India is English-only and urban-focused. Nyay AI takes questions in Hindi/Hinglish and answers in simple Hindi.
- **Grounded in real law, not guesses.** Every answer is generated from text retrieved from the Consumer Protection Act, 2019 and the Tamil Nadu Landlords and Tenants Act, 2017, instead of a general-purpose chatbot's memory.
- **100% local, zero paid APIs.** Embeddings, vector database and LLM all run on the user's own machine (ChromaDB + multilingual-e5 + Ollama). No API keys, no per-query cost, and queries never leave the device.
- **Built-in hallucination control.** A fixed system prompt forces the model to stay within retrieved context, say "jaankari nahi mili" when the topic is not covered, and always end with a "this is information, not legal advice" disclaimer.
- **Runs on a modest laptop.** Tuned to work on an 8 GB RAM machine using a lightweight model (gemma3:4b), with llama3 as an optional heavier choice.

---

## How it works

```
User question (Hindi)
        |
        v
Embed query (multilingual-e5-base)
        |
        v
ChromaDB similarity search -> top 5 legal chunks
        |
        v
Prompt = fixed rules + retrieved chunks + question
        |
        v
Local LLM via Ollama (gemma3:4b / llama3)
        |
        v
Simple Hindi answer + disclaimer
```

---

## Tech stack

| Layer | Tool |
|---|---|
| PDF text extraction | pdfplumber |
| Cleaning and chunking | LangChain RecursiveCharacterTextSplitter |
| Embeddings | intfloat/multilingual-e5-base (sentence-transformers, local) |
| Vector store | ChromaDB (persistent, local) |
| LLM runtime | Ollama (gemma3:4b default, llama3 optional) |
| Language | Python 3.11 |

---

## Project structure

```
nyay-ai/
├── data/
│   ├── raw/                  # source PDFs
│   └── processed/            # extracted text + chunks.json
├── scripts/
│   ├── extract_pdf.py        # PDF -> text
│   ├── chunk_data.py         # clean + chunk -> chunks.json
│   ├── build_vectorstore.py  # embed chunks -> ChromaDB
│   ├── test_retrieval.py     # retrieval sanity check
│   └── rag_query.py          # full RAG: retrieval + LLM answer
├── vectorstore/              # ChromaDB storage (generated)
└── requirements.txt
```

---

## Work done so far

**1. Data collection and extraction**
- Collected the Consumer Protection Act, 2019 (India Code) and the Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act, 2017.
- Built `extract_pdf.py` to pull clean text out of the PDFs.

**2. Chunking**
- Built `chunk_data.py` to clean the text (extra whitespace, page numbers) and split it into 500-character chunks with 50-character overlap.
- Result: 438 retrieval-ready chunks, each tagged with its source Act.

**3. Embeddings and vector store**
- Embedded all chunks with multilingual-e5-base (using the correct `passage:` / `query:` prefixes) and stored them in a local ChromaDB collection.
- Verified retrieval with a Hindi-style query ("landlord deposit nahi de raha"); the top results were the relevant tenant-obligation, rent-deposit and rent-authority sections.

**4. End-to-end RAG pipeline**
- Connected retrieval to a local Ollama model in `rag_query.py`. The pipeline retrieves the top chunks, builds a grounded prompt, and returns a Hindi answer with a disclaimer.

**5. Iteration and debugging (what changed and why)**
- **Over-refusal fix.** The first prompt was too strict ("answer only from context") and the model replied "jaankari nahi mili" even when relevant principles were retrieved. The prompt now lets the model apply retrieved legal principles to the user's situation, while still forbidding invented facts, sections or numbers. This is the faithfulness vs. helpfulness trade-off in RAG.
- **Coverage.** Raised retrieval from top-3 to top-5 chunks.
- **Performance.** Raised the Ollama timeout from 120s to 300s because generation on an 8 GB CPU-only laptop is slow.
- **Environment.** Moved to Python 3.11 after Python 3.13 caused build failures with the ML dependencies.

---

## Setup and usage

```bash
# 1. Environment (use Python 3.11)
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# 2. Install Ollama (https://ollama.com) and pull a model
ollama pull gemma3:4b

# 3. Put the PDFs in data/raw/, then run the pipeline in order
python scripts/extract_pdf.py
python scripts/chunk_data.py
python scripts/build_vectorstore.py     # first run downloads the ~1 GB embedding model

# 4. Test retrieval, then ask a question
python scripts/test_retrieval.py "landlord deposit nahi de raha"
python scripts/rag_query.py "landlord deposit nahi de raha"
python scripts/rag_query.py "product kharab nikla refund kaise le" --model llama3
```

Source documents:
- Consumer Protection Act, 2019: https://www.indiacode.nic.in/bitstream/123456789/18964/1/cpa.pdf
- Tamil Nadu Regulation of Rights and Responsibilities of Landlords and Tenants Act, 2017 (India Code / Tamil Nadu government)

---

## Known limitations

- Tenant law currently covers Tamil Nadu only; consumer law is the central Act.
- Answers can be generic when the retrieved chunks only contain broad principles. Explicit section-number citations in the final answer are not implemented yet.
- Generation is slow on CPU-only machines with 8 GB RAM.
- Some questions (for example detailed e-commerce refund rules) need additional source documents beyond the two Acts.
- This tool provides legal information, not legal advice.

---

## Roadmap

- [x] Data extraction, chunking, embeddings, vector store
- [x] Local RAG pipeline with Hindi answers and disclaimer
- [ ] Systematic hallucination testing on 15-20 real-world queries
- [ ] Explicit section-number citations in answers
- [ ] Template-based legal notice / complaint draft generator
- [ ] Streamlit web UI
- [ ] Voice input in Hindi (Whisper, local)
- [ ] Document upload (PDF/image) with OCR: deadline extraction, action checklist, fake-notice red flags, reply drafting
- [ ] More laws and states (labour rights, RTI, other state tenancy acts)

---

## Disclaimer

Nyay AI provides general legal information only. It is not a substitute for advice from a qualified lawyer. For your specific case, contact a lawyer or your nearest Legal Services Authority / Legal Aid Clinic.

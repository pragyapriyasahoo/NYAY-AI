# Nyay AI — Vernacular Legal-Rights RAG Assistant

Hindi-first RAG assistant for Consumer Protection & Tenant Rights law.
No paid APIs — fully local stack (Ollama + ChromaDB + open embeddings).

## Folder structure
```
nyay-ai/
├── data/
│   ├── raw/          # downloaded PDFs/text (Consumer Protection Act, Tenant laws, NALSA docs)
│   └── processed/    # cleaned + chunked .json/.md files ready for embedding
├── scripts/
│   ├── extract_pdf.py    # Phase 1: pull text out of PDFs
│   └── chunk_data.py      # Phase 2: clean + chunk into retrieval units
├── vectorstore/       # ChromaDB persistent storage (auto-created)
└── requirements.txt
```

## Setup (do this first)
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Install Ollama separately (not a pip package): https://ollama.com/download
Then run:
```bash
ollama pull llama3
```

## Build order (follow in sequence — don't skip ahead)
- [ ] Phase 1: Drop raw PDFs into `data/raw/` → run `extract_pdf.py`
- [ ] Phase 2: Run `chunk_data.py` → check `data/processed/`
- [ ] Phase 3: Embed chunks into ChromaDB (script added once Phase 1-2 done)
- [ ] Phase 4: Connect Ollama + LangChain retrieval chain
- [ ] Phase 5: Test hallucination on 15-20 sample queries
- [ ] Phase 6: Draft-generator templates
- [ ] Phase 7: Streamlit UI
- [ ] Phase 8 (later): Whisper voice input

## Data sources to download into data/raw/
1. Consumer Protection Act 2019 — indiacode.nic.in
2. Your state's Rent Control / Tenancy Act — indiacode.nic.in
3. NALSA explainer PDFs — nalsa.gov.in (already simplified language, high value)

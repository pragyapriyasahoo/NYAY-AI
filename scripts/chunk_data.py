"""
Phase 2: Clean + chunk the extracted .txt files into retrieval-ready units.
Run this after extract_pdf.py has produced .txt files in data/processed/.

Usage:
    python scripts/chunk_data.py
"""

import json
import re
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
CHUNKS_OUT = PROCESSED_DIR / "chunks.json"

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " "],
)


def clean_text(text: str) -> str:
    """Remove extra whitespace, repeated newlines, page-number noise."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)  # lone page numbers
    return text.strip()


def main():
    txt_files = list(PROCESSED_DIR.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {PROCESSED_DIR}. Run extract_pdf.py first.")
        return

    all_chunks = []

    for txt_path in txt_files:
        raw = txt_path.read_text(encoding="utf-8")
        cleaned = clean_text(raw)
        pieces = splitter.split_text(cleaned)

        for i, piece in enumerate(pieces):
            all_chunks.append({
                "id": f"{txt_path.stem}_{i}",
                "text": piece,
                "source": txt_path.stem,   # e.g. "consumer_protection_act"
            })

        print(f"{txt_path.name}: {len(pieces)} chunks")

    CHUNKS_OUT.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal chunks: {len(all_chunks)}")
    print(f"Saved to {CHUNKS_OUT}")


if __name__ == "__main__":
    main()

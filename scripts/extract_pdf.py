"""
Phase 1: Extract raw text from PDFs in data/raw/
Run this after dropping PDFs (Consumer Protection Act, Tenant laws, NALSA docs)
into the data/raw/ folder.

Usage:
    python scripts/extract_pdf.py
"""

import pdfplumber
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Pull plain text out of a single PDF, page by page."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def main():
    pdf_files = list(RAW_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {RAW_DIR}. Drop your Act/NALSA PDFs there first.")
        return

    for pdf_path in pdf_files:
        print(f"Extracting: {pdf_path.name}")
        raw_text = extract_text_from_pdf(pdf_path)

        out_path = OUT_DIR / f"{pdf_path.stem}.txt"
        out_path.write_text(raw_text, encoding="utf-8")
        print(f"  -> saved to {out_path}")

    print(f"\nDone. {len(pdf_files)} file(s) extracted to {OUT_DIR}")


if __name__ == "__main__":
    main()

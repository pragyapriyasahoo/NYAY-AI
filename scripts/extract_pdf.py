"""
Phase 1: Extract raw text from PDFs in data/raw/
Run this after dropping PDFs (Consumer Protection Act, Tenant laws, NALSA docs)
into the data/raw/ folder.

Usage:
    python scripts/extract_pdf.py
"""

import pdfplumber
import re
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Patterns for cleaning during extraction
GAZETTE_HEADER = re.compile(r"^\d*\s*TAMIL NADU GOVERNMENT GAZETTE EXTRAORDINARY\s*\d*\s*$", re.MULTILINE)
SINGLE_LETTER_LINE = re.compile(r"^[A-Za-z]\s*$", re.MULTILINE)
# Single letter on a line with leading whitespace (e.g., "  e" or "  d" at end of wrapped lines)
SINGLE_LETTER_INDENTED = re.compile(r"^\s+[A-Za-z]\s*$", re.MULTILINE)
# Single letter at end of line after punctuation (e.g., "; e" or "; d")
TRAILING_SINGLE_LETTER = re.compile(r";\s+[A-Za-z]\s*$", re.MULTILINE)
LONE_PAGE_NUMBER = re.compile(r"^\s*\d+\s*$", re.MULTILINE)

# Footnote and notification blocks - more comprehensive
FOOTNOTE_BLOCK = re.compile(
    r"^\s*\*\.\s*Vide\s+Notifn\..*?(?=\n\s*\(\d+\)|\n\s*\d+\.\s|\n\s*[A-Z]|\Z)",
    re.MULTILINE | re.DOTALL
)
NOTIFICATION_BLOCK = re.compile(
    r"^\s*\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*[—-].*?(?=^\s*\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*[—-]|\n\s*\(\d+\)|\n\s*\d+\.\s|\Z)",
    re.MULTILINE | re.DOTALL
)
# Additional notification pattern: "No. S.O. XXXX(E), dated..."
SO_NOTIFICATION = re.compile(
    r"^\s*No\.\s*S\.O\.\s*\d+\(E\).*?(?=\n\s*\(\d+\)|\n\s*\d+\.\s|\n\s*[A-Z]|\Z)",
    re.MULTILINE | re.DOTALL
)
# Catch remaining notification continuations like "Kashmir and the Union territory of Ladakh"
# and multi-line notification blocks starting with date
NOTIFICATION_CONTINUATION = re.compile(
    r"^\s*(?:Kashmir and the Union territory of Ladakh|vide Notifn\.|see Gazette of India).*?(?=\n\s*\(\d+\)|\n\s*\d+\.\s|\n\s*[A-Z]\"|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE
)
# Catch date-starting notification lines (e.g., "1. 20th July, 2020.—S. 2 ...")
DATE_NOTIFICATION = re.compile(
    r"^\s*\d+\.\s+\d{1,2}(?:st|nd|rd|th)\s+\w+,\s+\d{4}\.\s*.*?(?=\n\s*\(\d+\)|\n\s*\d+\.\s|\Z)",
    re.MULTILINE | re.DOTALL
)
# Inline margin headings in TN Act: section title words appear inline after "shall" or similar
# e.g., "20. (1) No landlord... shall Cutting off or cut-off or withhold..." 
# The words "Cutting off or" are from the section title "Cutting off or withholding essential supply or service"
INLINE_MARGIN_HEADING = re.compile(
    r'(shall\s+)([A-Z][a-z]+(?:\s+[A-Za-z]+){1,4}\s+)(?=[a-z]|withhold|cut|withholding|essential)',
    re.DOTALL
)
# Margin headings appearing mid-sentence: lowercase word followed by TitleCase section title word
# e.g., "tenancy Repossession agreement" -> remove "Repossession"
# Exclude common legal/administrative words that are NOT margin headings
COMMON_LEGAL_WORDS = r"(?:Court|Government|Authority|Commission|Tribunal|Act|Section|Schedule|State|Central|District|National|Supreme|High|Rent|Landlord|Tenant|Property|Manager|Agreement|Notice|Order|Appeal|Revision|Deposit|Receipt|Repair|Maintenance|Essential|Supply|Service|Possession|Occupation|Vacancy|Compensation|Advance|Refund|Permission|Structure|Site|Jurisdiction|Procedure|Power|Function|Appointment|Rules|Regulations|Savings|Repeal)"
MARGIN_INLINE_MID = re.compile(
    rf'([a-z])\s+(?!{COMMON_LEGAL_WORDS}\b)([A-Z][a-z]+)\s+(?=[a-z]|agreement|premises|order|tenant|landlord|grounds)',
    re.MULTILINE
)

# Broken words mapping (pattern -> replacement)
BROKEN_WORDS = [
    (r"byhimself", "by himself"),
    (r"andinform\b", "and inform"),
    (r"foIr\b", "for"),
    (r"forI\b", "for"),
    (r"icase\b", "the case"),
    (r"caise\b", "case"),
    (r"commeorcial\b", "commercial"),
    (r"commercioal\b", "commercial"),
    (r"Governeent\b", "Government"),
    (r"Aoct\b", "Act"),
    (r"Pd\s+ROTECTION\b", "PROTECTION"),
    (r"PROd\s+TECTION\b", "PROTECTION"),
    (r"commisesion\b", "commission"),
    (r"businesds\b", "business"),
    (r"enCtities\b", "entities"),
    (r"statemaent\b", "statement"),
    (r"cionforms\b", "conforms"),
    (r"cut.?off\s+or\s+cut.?off", "cut off or withhold"),
]


def clean_extracted_text(text: str, is_tn_act: bool = False) -> str:
    """Clean raw PDF text before saving."""
    # Remove gazette headers
    text = GAZETTE_HEADER.sub("", text)
    # Remove single-letter lines (watermarks)
    text = SINGLE_LETTER_LINE.sub("", text)
    # Remove single-letter lines with indentation (wrapped line artifacts)
    text = SINGLE_LETTER_INDENTED.sub("", text)
    # Remove trailing single letters after punctuation (e.g., "; e")
    text = TRAILING_SINGLE_LETTER.sub(";", text)
    # Remove lone page numbers
    text = LONE_PAGE_NUMBER.sub("", text)
    # Remove footnote and notification blocks
    text = FOOTNOTE_BLOCK.sub("", text)
    text = NOTIFICATION_BLOCK.sub("", text)
    text = SO_NOTIFICATION.sub("", text)
    text = NOTIFICATION_CONTINUATION.sub("", text)
    text = DATE_NOTIFICATION.sub("", text)
    # TN Act specific cleaning
    if is_tn_act:
        # Remove inline margin headings (TN Act specific) - keep 'shall ' but remove the title words
        text = INLINE_MARGIN_HEADING.sub(r"\1", text)
        # Remove margin headings appearing mid-sentence (TN Act specific) - keep the preceding word
        text = MARGIN_INLINE_MID.sub(r"\1 ", text)
    # Fix broken words
    for pattern, repl in BROKEN_WORDS:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Pull plain text out of a single PDF, page by page."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    raw = "\n".join(text_parts)
    # Apply TN-specific cleaning only for TN Act
    is_tn_act = "tamil nadu" in pdf_path.name.lower() or "landlords" in pdf_path.name.lower()
    return clean_extracted_text(raw, is_tn_act=is_tn_act)


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
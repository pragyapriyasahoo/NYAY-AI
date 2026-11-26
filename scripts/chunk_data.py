"""
Section-wise chunking (replaces chunk_data.py).

Each chunk is a piece of ONE legal section and starts with a header like
"Section 11. Security deposit." so retrieval and citations know which
section it belongs to.

How it works:
  1. Reads the table of contents at the top of each Act ("11.Security deposit.")
     to learn section numbers and titles.
  2. Finds where each section really starts in the body, in order.
  3. Splits long sections into ~1200-char pieces (header repeated on each).
  4. If a file has no usable table of contents, falls back to plain splitting.

Usage:
    python scripts/chunk_sections.py
    python scripts/chunk_sections.py --show 11     # print chunks of section 11
"""

import re
import json
import argparse
from pathlib import Path

PROCESSED = Path(__file__).parent.parent / "data" / "processed"
OUT = PROCESSED / "chunks.json"
MAX_CHARS = 1200
OVERLAP = 150

# TOC line: "1. Short title, extent, commencement and application." or "10.Rent Authority to fix or revise rent."
TOC_LINE = re.compile(r"^\s*(\d{1,3})\.\s*([A-Z][^\n]{2,150}?)\s*$")


def clean(text: str) -> str:
    """Clean text after extraction (extract_pdf.py does initial cleaning)."""
    text = text.replace("\r", "")
    # Normalize whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove any remaining lone page numbers
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Remove any remaining gazette headers
    text = re.sub(r"^\s*\d*\s*TAMIL NADU GOVERNMENT GAZETTE EXTRAORDINARY\s*\d*\s*$",
                  "", text, flags=re.MULTILINE)
    # Remove any remaining single-letter watermark lines
    text = re.sub(r"^[A-Za-z]$", "", text, flags=re.MULTILINE)
    # Fix common broken words from PDF extraction
    text = re.sub(r"byhimself", "by himself", text)
    text = re.sub(r"andinform\b", "and inform", text)
    text = re.sub(r"foIr\b", "for", text)
    text = re.sub(r"icase\b", "the case", text)
    text = re.sub(r"commeorcial\b", "commercial", text)
    text = re.sub(r"Governeent\b", "Government", text)
    text = re.sub(r"Aoct\b", "Act", text)
    text = re.sub(r"Pd\s+ROTECTION", "PROTECTION", text)
    # Fix duplicate "cut-off or cut-off" -> "cut off or withhold"
    text = re.sub(r"cut.?off\s+or\s+cut.?off", "cut off or withhold", text, flags=re.IGNORECASE)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_toc(text: str):
    """Return ({section_no: title}, char offset where the body begins).
    
    For CPA: skip amendment notes, find 'ARRANGEMENT OF SECTIONS' then parse.
    For TN: parse the 'Arrangement of Clauses' section.
    """
    lines = text.split("\n")
    expected, toc, last_idx, offset, pos = 1, {}, -1, 0, 0
    line_starts = []
    for line in lines:
        line_starts.append(pos)
        pos += len(line) + 1

    # Find the TOC region: look for "ARRANGEMENT OF SECTIONS" or "Arrangement of Clauses"
    toc_start = 0
    for i, line in enumerate(lines):
        if re.search(r"ARRANGEMENT OF (SECTIONS|CLAUSES)", line, re.IGNORECASE):
            toc_start = i + 1
            break

    # Parse TOC entries from toc_start until end of TOC region
    # TOC region ends at "First Schedule", "Second Schedule", "Third Schedule", 
    # or the enacting clause "BE it enacted"
    toc_end = len(lines)
    for i in range(toc_start, len(lines)):
        line = lines[i]
        if re.search(r"(FIRST|SECOND|THIRD)\s+SCHEDULE", line, re.IGNORECASE):
            toc_end = i
            break
        if re.search(r"^BE it enacted", line, re.IGNORECASE):
            toc_end = i
            break

    # Parse all TOC entries in the region, not just sequential
    # Collect all matches first, then sort by section number
    toc_matches = []
    for i in range(toc_start, toc_end):
        line = lines[i]
        m = TOC_LINE.match(line)
        if m:
            num = int(m.group(1))
            title = m.group(2).strip().rstrip(".")
            toc_matches.append((num, title, i))

    # Build toc dict from matches, taking the first occurrence of each section number
    for num, title, idx in toc_matches:
        if num not in toc:
            toc[num] = title
            if num == expected:
                expected = num + 1
            last_idx = max(last_idx, idx)

    if toc:
        offset = line_starts[min(last_idx + 1, len(lines) - 1)]
    return toc, offset


BODY_END_MARKERS = re.compile(
    r"(?m)^(THE FIRST SCHEDULE|STATEMENT OF OBJECTS AND REASONS|FINANCIAL MEMORANDUM)")


def find_body_end(text: str, body_start: int) -> int:
    """Where the numbered sections stop (schedules / forms / objects come after)."""
    m = BODY_END_MARKERS.search(text, body_start)
    return m.start() if m else len(text)


def locate_sections(text: str, toc: dict, body_start: int, body_end: int):
    """Find the start offset of each section in the body, in order.
    Takes the EARLIEST of two layouts: number at line start ("11.(1) ..."), or
    margin heading on the same line ("Rent payable. 8. The rent ...")."""
    starts, pos = [], body_start
    for n in sorted(toc):
        strict = re.compile(rf"(?m)^[ \t]*{n}\.[ \t]*(?=[\(\"\u201cA-Za-z])")
        loose = re.compile(rf"(?m)^([^\n]{{0,90}}?)[ \t]{n}\.[ \t]*(?=[\(\"\u201cA-Z])")

        cands = []
        m = strict.search(text, pos, body_end)
        if m:
            cands.append((m.start(), m.end()))
        for m in loose.finditer(text, pos, body_end):
            tail = m.group(1).lower().split(". ")[-1]
            if re.search(r"\b(sections?|clauses?|rules?|schedule)\b", tail):
                continue  # looks like a cross-reference ("under section 8."), not a section start
            cands.append((m.start() + len(m.group(1)) + 1, m.end()))
            break
        if cands:
            start, end = min(cands)
            starts.append((n, start))
            pos = end
    return starts


def split_long(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP):
    parts, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            cut = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            if cut > start + max_chars // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


def chunk_file(path: Path):
    stem = path.stem
    text = clean(path.read_text(encoding="utf-8"))
    toc, body_start = parse_toc(text)
    chunks = []

    if len(toc) < 5:
        print(f"{path.name}: no usable table of contents, using plain splitting")
        for i, part in enumerate(split_long(text)):
            chunks.append({"id": f"{stem}_{i}", "text": part, "source": stem,
                           "section": "", "title": ""})
        return chunks

    body_end = find_body_end(text, body_start)
    starts = locate_sections(text, toc, body_start, body_end)
    missing = [n for n in toc if n not in dict(starts)]
    print(f"{path.name}: TOC sections={len(toc)}, located in body={len(starts)}, "
          f"missing={missing if missing else 'none'}")

    for idx, (n, s) in enumerate(starts):
        e = starts[idx + 1][1] if idx + 1 < len(starts) else body_end
        body = text[s:e].strip()
        ch = re.search(r"(?m)^CHAPTER\s+[IVXL]+\.?\s*$", body)
        if ch:
            body = body[:ch.start()].strip()
        title = toc[n]
        header = f"Section {n}. {title}."
        for k, part in enumerate(split_long(body)):
            label = header if k == 0 else f"{header} (continued)"
            chunks.append({"id": f"{stem}_s{n}_{k}", "text": f"{label}\n{part}",
                           "source": stem, "section": str(n), "title": title})
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="print the chunks of this section number")
    args = ap.parse_args()

    files = sorted(PROCESSED.glob("*.txt"))
    if not files:
        print(f"No .txt files in {PROCESSED}. Run extract_pdf.py first.")
        return

    all_chunks = []
    for f in files:
        all_chunks.extend(chunk_file(f))

    OUT.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal chunks: {len(all_chunks)}  ->  {OUT}")

    if args.show:
        print(f"\n--- Chunks for section {args.show} ---")
        for c in all_chunks:
            if c["section"] == args.show:
                print(f"\n[{c['source'][:40]}]\n{c['text']}\n")


if __name__ == "__main__":
    main()
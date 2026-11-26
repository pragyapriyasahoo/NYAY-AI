# Phase A Plan: Data Quality Fixes

## Problems to Fix

### 1. CPA Section 1 Title Wrong
- Current: "The Turbinal Reforms Act, 2021 (33 of 2021)" (from amendment note in TOC)
- Expected: "Short title, extent, commencement and application."
- Root cause: TOC parser picks up the amendment note line before the actual TOC entries

### 2. PDF Extraction Noise (both Acts)
- **Margin headers**: "TAMIL NADU GOVERNMENT GAZETTE EXTRAORDINARY 405" interleaved in text
- **Single-letter lines**: "e", "d", "o", "C", "a", "i", "d", "n", "I" appearing as separate lines
- **Broken words**: "Governeent", "Aoct", "icase", "foIr", "commeorcial", "byhimself"
- **Duplicate words**: "cut-off or cut-off"
- **Footnotes leaking**: "*. Vide Notifn. No. S.O. 3912(E), dated 30th October, 2019..."
- **Page numbers**: Standalone numbers on lines

### 3. CPA Section Numbers Verification
- Need to verify CPA section numbers against actual PDF text
- Current eval cases use placeholder section numbers

## Files to Modify

1. `scripts/extract_pdf.py` - Improve text extraction cleaning
2. `scripts/chunk_data.py` - Fix TOC parsing for CPA, improve text cleaning in `clean()` function
3. Re-run extraction → chunking → vector store build
4. `scripts/diagnose.py` - Verify fixes

## Implementation Steps

1. **Fix `extract_pdf.py`**: Add better cleaning during extraction (remove margin headers, single letters, page numbers)
2. **Fix `chunk_data.py`**:
   - Improve `clean()` function to handle broken words, duplicate words, footnotes
   - Fix `parse_toc()` for CPA to skip amendment notes
   - Improve section location logic
3. **Re-extract PDFs**: `python scripts/extract_pdf.py`
4. **Re-chunk**: `python scripts/chunk_data.py`
5. **Rebuild vector store**: `python scripts/build_vectorstore.py`
6. **Verify**: `python scripts/diagnose.py` and spot-check 10 random chunks

## Gate Criteria
- `diagnose.py` shows correct titles for all sections
- Spot check of 10 random chunks shows clean text (no margin headers, no single letters, no broken words, no duplicate words)
- CPA section 1 title is "Short title, extent, commencement and application."
- TN Act all 47 sections still found with correct titles
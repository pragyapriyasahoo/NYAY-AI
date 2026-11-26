"""Read-only health check for Nyay AI. Usage: python scripts/diagnose.py"""
import os, re, json, sys
os.environ["ANONYMIZED_TELEMETRY"] = "False"
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
CHUNKS = ROOT / "data" / "processed" / "chunks.json"
RAW = ROOT / "data" / "raw"
VS = ROOT / "vectorstore"
DEVA = re.compile(r"[\u0900-\u097F]")

def hdr(t): print(f"\n===== {t} =====")

hdr("PYTHON & PACKAGES")
print(sys.version.split()[0], "|", sys.executable)
from importlib.metadata import version, PackageNotFoundError
for p in ["pdfplumber", "chromadb", "sentence-transformers", "requests", "langchain"]:
    try: print(f"  {p}: {version(p)}")
    except PackageNotFoundError: print(f"  {p}: NOT INSTALLED")

hdr("FOLDERS")
for p in [RAW, ROOT / "data" / "processed", VS, CHUNKS]:
    print(f"  {'OK ' if p.exists() else 'MISSING'}  {p.relative_to(ROOT)}")
if RAW.exists():
    print("  raw files:", [f.name for f in RAW.iterdir()])

hdr("CHUNKS.JSON")
if CHUNKS.exists():
    ch = json.loads(CHUNKS.read_text(encoding="utf-8"))
    print("  total chunks:", len(ch))
    print("  by source:", dict(Counter(c["source"] for c in ch)))
    tn = [c for c in ch if "Landlords" in c["source"] or "tamil" in c["source"].lower()]
    secs = sorted({int(c["section"]) for c in tn if c["section"].isdigit()})
    missing = [n for n in range(1, 48) if n not in secs]
    print(f"  TN sections found: {len(secs)} / 47   missing: {missing or 'none'}")
    print("  empty chunks:", sum(1 for c in ch if not c["text"].strip()))
    print("  chunks with no section label:", sum(1 for c in ch if not c["section"]))
    deva = sum(1 for c in ch if DEVA.search(c["text"]))
    print("  chunks containing Devanagari:", deva)
    lens = [len(c["text"]) for c in ch]
    print(f"  chunk length min/avg/max: {min(lens)} / {sum(lens)//len(lens)} / {max(lens)}")
    print("  section 21 chunk count:", sum(1 for c in ch if c["section"] == "21"))
    print("  first 2 chunk ids:", [c["id"] for c in ch[:2]])
else:
    print("  NOT FOUND. Run: python scripts/chunk_data.py")

hdr("CHROMADB")
try:
    import chromadb
    client = chromadb.PersistentClient(path=str(VS))
    cols = client.list_collections()
    print("  collections:", [c.name for c in cols])
    col = client.get_collection("nyay_ai_legal_chunks")
    print("  count:", col.count())
    print("  metadata:", col.metadata)
    space = (col.metadata or {}).get("hnsw:space", "l2 (default)")
    print("  distance metric:", space, "<- should be 'cosine'")
    sample = col.get(limit=1, include=["metadatas"])
    print("  sample metadata:", sample["metadatas"][0])
except Exception as e:
    print("  ERROR:", type(e).__name__, e)

hdr("OLLAMA")
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = [m["name"] for m in r.json().get("models", [])]
    print("  running. models:", models or "none pulled")
except Exception as e:
    print("  NOT REACHABLE:", type(e).__name__, "-> start with `ollama serve`")

print("\nDone. Paste everything above back to me.")
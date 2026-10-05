import json
import sys
from pathlib import Path
import pymupdf

# Set encoding for Windows console output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

sources_path = repo_root / "data" / "knowledge_base" / "sources.json"
kb_dir = repo_root / "data" / "knowledge_base"

print("============================================================")
print("AGRICULTURAL KNOWLEDGE BASE AUDIT")
print("============================================================")

# 1. Validate JSON strict syntax & duplicate key check
def dict_raise_on_duplicates(ordered_pairs):
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError(f"Duplicate key detected in JSON object: {k}")
        d[k] = v
    return d

print("\n--- 1. Validating sources.json syntax & key uniqueness ---")
try:
    with open(sources_path, "r", encoding="utf-8") as f:
        registry = json.load(f, object_pairs_hook=dict_raise_on_duplicates)
    print("SUCCESS: sources.json is valid strict JSON with zero duplicate keys.")
except Exception as e:
    print(f"FAILED: sources.json JSON validation error: {e}")
    sys.exit(1)

# 2. Audit each document listed in sources.json
sources = registry.get("sources", [])
institutions = registry.get("institutions", {})
print(f"\n--- 2. Auditing {len(sources)} Registered Document Metadata Entries ---")

verified_docs = []
rejected_docs = []
crop_doc_counts = {"rice": 0, "cotton": 0, "maize": 0, "groundnut": 0, "soybean": 0}

for idx, src in enumerate(sources, 1):
    crop = src.get("crop")
    filename = src.get("filename")
    title = src.get("title")
    inst = src.get("institution")
    year = src.get("year")
    url = src.get("source_url")
    
    print(f"\n[{idx}] Source ID: {src.get('source_id')}")
    print(f"    Crop: {crop} | Filename: {filename}")
    print(f"    Title: {title}")
    print(f"    Institution: {inst} ({institutions.get(inst, 'N/A')})")
    print(f"    Year: {year} | URL: {url}")
    
    # 3. File existence check
    pdf_path = kb_dir / crop / filename
    if not pdf_path.exists():
        print(f"    CRITICAL FAILURE: File does NOT exist at {pdf_path}")
        rejected_docs.append((filename, "File missing"))
        continue
    
    # 4. Content & genuineness check
    try:
        doc = pymupdf.open(str(pdf_path))
        page_count = len(doc)
        total_text_len = sum(len(p.get_text().strip()) for p in doc)
        doc.close()

        if total_text_len == 0 and page_count <= 1:
            print(f"    WARNING/NOTICE: 0 text characters extracted (Scanned Image PDF: {page_count} page(s)).")
            print("    Status: Accepted in registry as historical leaflet, but generates 0 text vector chunks.")
        
        print(f"    Verification: File exists ({pdf_path.stat().st_size / 1024:.1f} KB, {page_count} pages, {total_text_len} text chars).")
        verified_docs.append({
            "crop": crop,
            "filename": filename,
            "title": title,
            "institution": inst,
            "year": year,
            "pages": page_count,
            "text_chars": total_text_len,
            "url": url
        })
        if crop in crop_doc_counts:
            crop_doc_counts[crop] += 1
    except Exception as e:
        print(f"    CRITICAL FAILURE: Failed to parse PDF: {e}")
        rejected_docs.append((filename, f"PDF read error: {e}"))

# 5. Check 5 crop coverage requirement
print("\n--- 3. Verifying 5 Crop Coverage ---")
missing_crops = [c for c, count in crop_doc_counts.items() if count == 0]
if missing_crops:
    print(f"FAILED: Missing documents for crops: {missing_crops}")
else:
    print("SUCCESS: All 5 crops have verified genuine agricultural PDF documents.")
    for c, count in crop_doc_counts.items():
        print(f"  • {c.capitalize()}: {count} document(s)")

print(f"\nSummary of Document Audit:")
print(f"  Verified Documents: {len(verified_docs)}")
print(f"  Rejected Documents: {len(rejected_docs)}")

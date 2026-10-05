import sys
from pathlib import Path
from typing import Dict, List

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.retrieval_service import retrieval_service

test_queries: Dict[str, str] = {
    "rice": "How to manage blast disease, nutrient management, and irrigation in rice?",
    "cotton": "What is the integrated pest management for pink bollworm and sucking pests in cotton?",
    "maize": "How to control Fall Armyworm and apply fertilizers in maize crop?",
    "groundnut": "What are the recommended practices for Tikka disease and water management in groundnut?",
    "soybean": "How to manage yellow mosaic virus and weed control in soybean?"
}

def verify_retrieval():
    print("============================================================")
    print("AgriIntel AI — Metadata & Retrieval Verification (5 Crops)")
    print("============================================================")

    results_summary = {}

    for crop, query in test_queries.items():
        print(f"\n================ CROP: {crop.upper()} ================")
        print(f"Query: \"{query}\"")
        chunks = retrieval_service.retrieve(query=query, crop=crop, top_k=3)
        
        results_summary[crop] = {
            "retrieved_count": len(chunks),
            "chunks": []
        }

        if not chunks:
            print("  FAILED: No chunks returned.")
            continue

        for idx, chk in enumerate(chunks, 1):
            clean_snippet = chk.text[:120].replace('\n', ' ').encode('ascii', errors='ignore').decode('ascii')
            chunk_info = {
                "source": chk.source,
                "title": chk.title,
                "crop": chk.crop,
                "page": chk.page,
                "year": chk.year,
                "score": chk.score,
                "snippet": clean_snippet
            }
            results_summary[crop]["chunks"].append(chunk_info)

            print(f"  [{idx}] Title: {chk.title}")
            print(f"      Source: {chk.source} | Crop: {chk.crop} | Page: {chk.page} | Year: {chk.year} | Score: {chk.score:.4f}")
            print(f"      Snippet: {clean_snippet}...\n")

    print("============================================================")
    all_ok = all(v["retrieved_count"] > 0 for v in results_summary.values())
    print(f"Overall Status: {'PASSED (5/5 crops verified)' if all_ok else 'FAILED'}")
    print("============================================================")

if __name__ == "__main__":
    verify_retrieval()

"""
Retrieval Evaluation Script.

Evaluates RAG retrieval against data/evaluation/benchmark_queries.json.
Reports verifiable empirical metrics:
- Query-by-query retrieval output
- Expected topic keyword match rate
- Crop filter precision
- Vector store document count
"""

import json
from pathlib import Path
from typing import Dict, Any, List

from app.core.config import settings
from app.services.retrieval_service import retrieval_service
from app.rag.vector_store import vector_store


def evaluate_retrieval(top_k: int = 4) -> Dict[str, Any]:
    """Run benchmark queries and calculate actual retrieval performance."""
    benchmark_file = settings.evaluation_dir / "benchmark_queries.json"
    if not benchmark_file.exists():
        print(f"Benchmark file not found at {benchmark_file}")
        return {}

    with open(benchmark_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = data.get("queries", [])
    total_queries = len(queries)
    doc_count = vector_store.count()

    print("=" * 70)
    print("AgriIntel AI — Retrieval Evaluation Report")
    print(f"ChromaDB Total Documents: {doc_count}")
    print(f"Total Benchmark Queries:   {total_queries}")
    print(f"Top-K:                     {top_k}")
    print("=" * 70)

    if doc_count == 0:
        print("\n[Notice] Vector database is currently empty.")
        print("Please place approved PDFs in data/knowledge_base/<crop>/ and run")
        print("'python scripts/build_knowledge_base.py' before running retrieval evaluation.\n")
        return {
            "total_queries": total_queries,
            "vector_count": 0,
            "hits": 0,
            "hit_rate": 0.0,
            "status": "empty_vector_store"
        }

    hits = 0
    crop_precision_matches = 0
    results_detail: List[Dict[str, Any]] = []

    print(f"{'ID':<12} | {'Crop':<10} | {'Found':<6} | {'Topic Hit':<10} | {'Top Source'}")
    print("-" * 70)

    for item in queries:
        qid = item["id"]
        crop = item["crop"]
        query_text = item["query"]
        expected_topics = item.get("expected_topics", [])

        chunks = retrieval_service.retrieve(query=query_text, crop=crop, top_k=top_k)

        # Check topic match in retrieved chunks
        combined_text = " ".join([c.text.lower() for c in chunks])
        topic_matched = any(topic.lower() in combined_text for topic in expected_topics)

        # Check crop filtering fidelity
        crop_correct = all(c.crop.lower() == crop.lower() for c in chunks) if chunks else True

        if topic_matched:
            hits += 1
        if crop_correct and chunks:
            crop_precision_matches += 1

        top_source = f"{chunks[0].source} (p.{chunks[0].page})" if chunks else "None"

        print(f"{qid:<12} | {crop:<10} | {len(chunks):<6} | {str(topic_matched):<10} | {top_source}")

        results_detail.append({
            "id": qid,
            "crop": crop,
            "chunks_retrieved": len(chunks),
            "topic_matched": topic_matched,
            "crop_precision": crop_correct,
            "top_chunk_score": chunks[0].score if chunks else None,
        })

    hit_rate = round((hits / total_queries) * 100, 2) if total_queries > 0 else 0.0
    crop_acc = round((crop_precision_matches / total_queries) * 100, 2) if total_queries > 0 else 0.0

    print("=" * 70)
    print(f"Topic Hit Rate (Recall@K): {hits}/{total_queries} ({hit_rate}%)")
    print(f"Crop Filter Accuracy:      {crop_precision_matches}/{total_queries} ({crop_acc}%)")
    print("=" * 70)

    return {
        "total_queries": total_queries,
        "vector_count": doc_count,
        "hits": hits,
        "hit_rate_percent": hit_rate,
        "crop_accuracy_percent": crop_acc,
        "details": results_detail,
    }


if __name__ == "__main__":
    evaluate_retrieval()

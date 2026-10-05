"""
Knowledge Base Builder Script.

Scans the data/knowledge_base/<crop>/ directories for genuine agricultural PDF documents,
extracts text page-by-page, chunks with page-level provenance, generates embeddings,
and indexes them into the local ChromaDB vector store.

Does not create or fabricate synthetic documents. If directories are empty, reports
the missing documents cleanly.
"""

from pathlib import Path
import sys

from app.core.config import settings
from app.services.ingestion_service import ingestion_service
from app.rag.vector_store import vector_store


def build_knowledge_base():
    """Scan and ingest approved agricultural PDFs into ChromaDB."""
    print("=" * 60)
    print("AgriIntel AI — Agricultural Knowledge Base Builder")
    print(f"Target Crops: {', '.join(settings.supported_crops)}")
    print(f"Knowledge Base Directory: {settings.knowledge_base_dir}")
    print(f"Vector Store Directory: {settings.chroma_db_dir}")
    print("=" * 60)

    # Check available documents
    total_found_pdfs = 0
    for crop in settings.supported_crops:
        crop_dir = settings.knowledge_base_dir / crop
        pdfs = list(crop_dir.glob("*.pdf")) if crop_dir.exists() else []
        total_found_pdfs += len(pdfs)
        status_msg = f"{len(pdfs)} PDF(s) found" if pdfs else "EMPTY (Awaiting original ICAR/approved PDFs)"
        print(f"  • {crop.capitalize():<12}: {status_msg}")

    if total_found_pdfs == 0:
        print("\n[Notice] No agricultural PDFs detected in data/knowledge_base/<crop>/.")
        print("Please place approved, original ICAR extension bulletins / publications")
        print("into the corresponding crop folder and re-run this script.")
        print(f"Current vector count in ChromaDB: {vector_store.count()}")
        return

    print("\nStarting ingestion and embedding generation...")
    result = ingestion_service.ingest_all_crops()

    print("\nIngestion Summary:")
    print(f"  Total files processed: {result['total_files']}")
    print(f"  Total chunks indexed:  {result['total_chunks_indexed']}")
    print(f"  ChromaDB total count:  {result['current_vector_count']}")
    print("=" * 60)


if __name__ == "__main__":
    build_knowledge_base()

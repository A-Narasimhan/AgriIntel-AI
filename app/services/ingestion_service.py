"""
Agricultural PDF document ingestion service using PyMuPDF.

Preserves page numbers and provenance metadata during text extraction,
chunking, embedding, and vector database indexing.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import pymupdf as fitz

from app.core.config import settings
from app.rag.chunker import chunk_page_text
from app.rag.metadata import create_chunk_id, validate_chunk_metadata, normalize_crop_name
from app.rag.vector_store import vector_store
from app.services.embedding_service import embedding_service


class IngestionService:
    """Handles parsing agricultural PDFs, generating embeddings, and storing in ChromaDB."""

    def __init__(self, sources_path: Optional[Path] = None, kb_dir: Optional[Path] = None):
        self.sources_path = sources_path or settings.sources_registry_path
        self.kb_dir = kb_dir or settings.knowledge_base_dir
        self.registry = self._load_sources_registry()

    def _load_sources_registry(self) -> Dict[str, Any]:
        """Load sources.json registry if it exists."""
        if self.sources_path.exists():
            try:
                with open(self.sources_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load sources registry: {e}")
        return {"sources": []}

    def _get_source_metadata(self, crop: str, filename: str) -> Dict[str, Any]:
        """Find matching source metadata from sources.json, or build sensible defaults."""
        sources = self.registry.get("sources", [])
        for src in sources:
            if src.get("crop") == crop and src.get("filename") == filename:
                return src

        # Fallback metadata if not explicitly registered in sources.json
        return {
            "source_id": f"{crop}-{Path(filename).stem}",
            "crop": crop,
            "title": f"ICAR Package of Practices for {crop.capitalize()}",
            "institution": "ICAR Research Institute",
            "year": 2024,
            "document_type": "technical_bulletin",
            "topic": "cultivation, disease_and_pest_management",
            "filename": filename,
        }

    def ingest_pdf(self, pdf_path: Path, crop: str) -> Dict[str, Any]:
        """
        Extract text from a single agricultural PDF page-by-page, chunk it with provenance,
        embed, and index into ChromaDB.
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        normalized_crop = normalize_crop_name(crop) or "general"
        source_meta = self._get_source_metadata(normalized_crop, pdf_path.name)

        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        all_chunks: List[Dict[str, Any]] = []

        for page_idx in range(total_pages):
            page = doc[page_idx]
            page_num = page_idx + 1  # 1-indexed page number
            page_text = page.get_text()

            base_meta = {
                "crop": normalized_crop,
                "source": pdf_path.name,
                "title": source_meta.get("title", f"{normalized_crop.capitalize()} Advisory"),
                "institution": source_meta.get("institution", "ICAR"),
                "year": source_meta.get("year", 2024),
                "topic": source_meta.get("topic", "crop_management"),
            }

            page_chunks = chunk_page_text(
                text=page_text,
                page_number=page_num,
                base_metadata=base_meta,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            all_chunks.extend(page_chunks)

        doc.close()

        if not all_chunks:
            return {
                "file": pdf_path.name,
                "crop": normalized_crop,
                "pages": total_pages,
                "chunks_indexed": 0,
                "status": "empty_or_no_text",
            }

        # Prepare for vector indexing
        chunk_ids: List[str] = []
        texts: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for chk in all_chunks:
            meta = validate_chunk_metadata(chk["metadata"])
            cid = create_chunk_id(meta["source"], meta["page"], meta["chunk_index"], chk["text"])
            chunk_ids.append(cid)
            texts.append(chk["text"])
            metadatas.append(meta)

        # Generate embeddings in batch
        embeddings = embedding_service.embed_texts(texts)

        # Store in ChromaDB
        indexed_count = vector_store.add_chunks(
            chunk_ids=chunk_ids,
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "file": pdf_path.name,
            "crop": normalized_crop,
            "pages": total_pages,
            "chunks_indexed": indexed_count,
            "status": "success",
        }

    def ingest_all_crops(self) -> Dict[str, Any]:
        """
        Scan all crop folders in data/knowledge_base/ and ingest all PDF documents.
        """
        results = {}
        total_chunks = 0
        total_files = 0

        for crop in settings.supported_crops:
            crop_dir = self.kb_dir / crop
            if not crop_dir.exists():
                continue

            pdf_files = list(crop_dir.glob("*.pdf"))
            crop_results = []

            for pdf in pdf_files:
                res = self.ingest_pdf(pdf, crop)
                crop_results.append(res)
                total_chunks += res.get("chunks_indexed", 0)
                total_files += 1

            results[crop] = {
                "files_count": len(pdf_files),
                "details": crop_results,
            }

        return {
            "total_files": total_files,
            "total_chunks_indexed": total_chunks,
            "crops": results,
            "current_vector_count": vector_store.count(),
        }


# Global instance
ingestion_service = IngestionService()

"""
Focused unit tests for the two ingestion_service fixes:

Fix 1 -- filter_crop=True passed to chunk_page_text:
    Cross-crop contaminated text must be rejected during ingestion, not indexed
    silently as a zero-quality chunk.

Fix 2 -- requires_ocr guard:
    Sources flagged as requires_ocr in sources.json must be skipped before
    PyMuPDF is even called.  The PDF file must remain untouched.
"""

from pathlib import Path
from unittest.mock import patch
import json
import pytest
import pymupdf as fitz

from app.services.ingestion_service import IngestionService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(sources: list, tmp_path: Path) -> IngestionService:
    """Return an IngestionService wired to a temporary sources.json."""
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps({"sources": sources}), encoding="utf-8"
    )
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()
    return IngestionService(sources_path=registry_path, kb_dir=kb_dir)


def _make_pdf(dest_dir: Path, filename: str, text: str = "content") -> Path:
    """Create a minimal single-page PDF with the given text content."""
    pdf_path = dest_dir / filename
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


# ---------------------------------------------------------------------------
# Fix 2 -- requires_ocr guard tests
# ---------------------------------------------------------------------------

class TestOcrSkip:
    """The service must skip OCR-flagged sources without opening the PDF."""

    def test_returns_skipped_status_when_requires_ocr_true(self, tmp_path):
        """ingest_pdf returns status skipped_requires_ocr for OCR-flagged PDFs."""
        sources = [{
            "source_id": "cotton-cicr-pbw-leaflet",
            "crop": "cotton",
            "filename": "cotton_pbw_management_cicr.pdf",
            "title": "CICR PBW Leaflet",
            "institution": "ICAR-CICR",
            "year": 2023,
            "requires_ocr": True,
            "ocr_status": "pending",
        }]
        svc = _make_service(sources, tmp_path)
        pdf_path = _make_pdf(tmp_path, "cotton_pbw_management_cicr.pdf", "dummy")

        result = svc.ingest_pdf(pdf_path, "cotton")

        assert result["status"] == "skipped_requires_ocr"
        assert result["chunks_indexed"] == 0
        assert result["pages"] == 0
        assert result["file"] == "cotton_pbw_management_cicr.pdf"

    def test_pdf_file_is_not_modified(self, tmp_path):
        """The PDF file mtime and size must be unchanged after a skip."""
        sources = [{
            "crop": "cotton",
            "filename": "cotton_pbw_management_cicr.pdf",
            "requires_ocr": True,
            "ocr_status": "pending",
        }]
        svc = _make_service(sources, tmp_path)
        pdf_path = _make_pdf(tmp_path, "cotton_pbw_management_cicr.pdf", "dummy")

        size_before = pdf_path.stat().st_size
        mtime_before = pdf_path.stat().st_mtime

        svc.ingest_pdf(pdf_path, "cotton")

        assert pdf_path.stat().st_size == size_before
        assert pdf_path.stat().st_mtime == mtime_before

    def test_warning_is_printed_for_ocr_skip(self, tmp_path, capsys):
        """A human-readable [SKIP] warning must be printed to stdout."""
        sources = [{
            "crop": "cotton",
            "filename": "cotton_pbw_management_cicr.pdf",
            "requires_ocr": True,
            "ocr_status": "pending",
        }]
        svc = _make_service(sources, tmp_path)
        pdf_path = _make_pdf(tmp_path, "cotton_pbw_management_cicr.pdf", "dummy")

        svc.ingest_pdf(pdf_path, "cotton")

        captured = capsys.readouterr()
        assert "[SKIP]" in captured.out
        assert "cotton_pbw_management_cicr.pdf" in captured.out
        assert "requires OCR" in captured.out

    def test_non_ocr_pdf_is_not_skipped(self, tmp_path):
        """A PDF without requires_ocr must not be skipped."""
        sources = [{
            "crop": "rice",
            "filename": "rice_test.pdf",
            "title": "Rice Advisory",
            "institution": "ICAR",
            "year": 2025,
            "topic": "cultivation",
        }]
        svc = _make_service(sources, tmp_path)
        pdf_path = _make_pdf(tmp_path, "rice_test.pdf", "Rice paddy cultivation. " * 20)

        with patch("app.services.ingestion_service.vector_store") as mock_vs, \
             patch("app.services.ingestion_service.embedding_service") as mock_emb:
            mock_emb.embed_texts.return_value = [[0.1] * 384]
            mock_vs.add_chunks.return_value = 1

            result = svc.ingest_pdf(pdf_path, "rice")

        assert result["status"] != "skipped_requires_ocr"

    def test_ingest_all_crops_counts_zero_for_ocr_skip(self, tmp_path):
        """ingest_all_crops must count 0 chunks for skipped OCR sources."""
        registry_path = tmp_path / "sources.json"
        registry_path.write_text(json.dumps({"sources": [
            {
                "crop": "cotton",
                "filename": "cotton_pbw_management_cicr.pdf",
                "requires_ocr": True,
                "ocr_status": "pending",
            }
        ]}), encoding="utf-8")

        kb_dir = tmp_path / "kb"
        cotton_dir = kb_dir / "cotton"
        cotton_dir.mkdir(parents=True)
        _make_pdf(cotton_dir, "cotton_pbw_management_cicr.pdf", "scanned dummy")

        svc = IngestionService(sources_path=registry_path, kb_dir=kb_dir)

        with patch("app.services.ingestion_service.vector_store") as mock_vs, \
             patch("app.services.ingestion_service.embedding_service"):
            mock_vs.count.return_value = 0
            result = svc.ingest_all_crops()

        details = result["crops"].get("cotton", {}).get("details", [])
        assert len(details) == 1
        assert details[0]["status"] == "skipped_requires_ocr"
        assert result["total_chunks_indexed"] == 0


# ---------------------------------------------------------------------------
# Fix 1 -- filter_crop=True passed to chunk_page_text
# ---------------------------------------------------------------------------

class TestFilterCropActivation:
    """chunk_page_text must always be called with filter_crop=True during ingestion."""

    def test_chunk_page_text_receives_filter_crop_true(self, tmp_path):
        """
        Patch chunk_page_text and verify filter_crop=True is always passed.
        """
        sources = [{
            "crop": "rice",
            "filename": "rice_test.pdf",
            "title": "Rice Advisory",
            "institution": "ICAR",
            "year": 2025,
            "topic": "cultivation",
        }]
        svc = _make_service(sources, tmp_path)
        pdf_path = _make_pdf(tmp_path, "rice_test.pdf", "Rice paddy farming. " * 15)

        with patch("app.services.ingestion_service.chunk_page_text") as mock_chunk, \
             patch("app.services.ingestion_service.vector_store") as mock_vs, \
             patch("app.services.ingestion_service.embedding_service") as mock_emb:

            mock_chunk.return_value = [{
                "text": "Rice paddy farming.",
                "metadata": {
                    "crop": "rice", "source": "rice_test.pdf",
                    "title": "Rice Advisory", "institution": "ICAR",
                    "year": 2025, "topic": "cultivation",
                    "page": 1, "chunk_index": 0,
                },
            }]
            mock_emb.embed_texts.return_value = [[0.1] * 384]
            mock_vs.add_chunks.return_value = 1

            svc.ingest_pdf(pdf_path, "rice")

        assert mock_chunk.call_count >= 1
        for c in mock_chunk.call_args_list:
            assert c.kwargs.get("filter_crop") is True, (
                f"chunk_page_text was called without filter_crop=True: {c}"
            )

    def test_cross_crop_text_not_indexed(self, tmp_path):
        """
        End-to-end: a page whose text is purely about another crop (maize)
        must produce zero indexed chunks when ingested as groundnut.
        """
        sources = [{
            "crop": "groundnut",
            "filename": "groundnut_test.pdf",
            "title": "Groundnut Advisory",
            "institution": "ICAR-DGR",
            "year": 2024,
            "topic": "cultivation",
        }]
        svc = _make_service(sources, tmp_path)

        # Text exclusively about maize -- should be filtered out for groundnut
        maize_text = (
            "Maize crop requires heavy nitrogen fertilisation. "
            "Fall armyworm in maize is controlled by chlorantraniliprole. " * 10
        )
        pdf_path = _make_pdf(tmp_path, "groundnut_test.pdf", maize_text)

        with patch("app.services.ingestion_service.vector_store") as mock_vs, \
             patch("app.services.ingestion_service.embedding_service") as mock_emb:
            mock_emb.embed_texts.return_value = []
            mock_vs.add_chunks.return_value = 0

            result = svc.ingest_pdf(pdf_path, "groundnut")

        # The cross-crop filter must eliminate all maize-only chunks
        assert result["chunks_indexed"] == 0
        assert result["status"] == "empty_or_no_text"

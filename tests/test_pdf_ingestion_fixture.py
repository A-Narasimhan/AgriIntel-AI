"""
Unit test for PyMuPDF PDF extraction and chunking pipeline using a minimal test fixture.
The test fixture contains non-agricultural dummy text and is kept strictly separate
from the production knowledge base.
"""

from pathlib import Path
import pymupdf as fitz
import pytest
from app.services.ingestion_service import IngestionService
from app.rag.chunker import chunk_page_text


@pytest.fixture
def dummy_pdf_fixture(tmp_path: Path) -> Path:
    """Create a minimal 2-page dummy PDF solely for testing extraction mechanics."""
    pdf_file = tmp_path / "dummy_test_doc.pdf"
    doc = fitz.open()

    p1 = doc.new_page()
    p1.insert_text((50, 50), "Dummy section 1 test content for page one. " * 10)

    p2 = doc.new_page()
    p2.insert_text((50, 50), "Dummy section 2 test content for page two. " * 10)

    doc.save(str(pdf_file))
    doc.close()
    return pdf_file


def test_pdf_extraction_page_preservation(dummy_pdf_fixture: Path):
    doc = fitz.open(str(dummy_pdf_fixture))
    assert len(doc) == 2

    # Verify page 1 extraction
    p1_text = doc[0].get_text()
    assert "Dummy section 1" in p1_text

    # Verify chunker preserves page number 1
    chunks_p1 = chunk_page_text(p1_text, page_number=1, base_metadata={"crop": "rice", "source": "dummy.pdf"})
    assert len(chunks_p1) >= 1
    assert chunks_p1[0]["metadata"]["page"] == 1

    # Verify page 2 extraction
    p2_text = doc[1].get_text()
    assert "Dummy section 2" in p2_text

    # Verify chunker preserves page number 2
    chunks_p2 = chunk_page_text(p2_text, page_number=2, base_metadata={"crop": "rice", "source": "dummy.pdf"})
    assert len(chunks_p2) >= 1
    assert chunks_p2[0]["metadata"]["page"] == 2

    doc.close()

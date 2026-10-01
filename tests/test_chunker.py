"""
Unit tests for text chunker and page boundary preservation.
"""

from app.rag.chunker import chunk_page_text, clean_text


def test_clean_text_removes_excessive_whitespace():
    raw = "Line 1   with spaces.\r\n\r\n\r\n\r\nLine 2.\n\nLine 3."
    cleaned = clean_text(raw)
    assert "\r" not in cleaned
    assert "Line 1 with spaces." in cleaned
    assert "\n\n\n" not in cleaned


def test_chunk_page_text_preserves_page_number():
    text = (
        "Agricultural guideline paragraph 1. " * 30 +
        "\n\nAgricultural guideline paragraph 2. " * 30
    )
    base_meta = {"crop": "rice", "source": "test.pdf"}
    chunks = chunk_page_text(
        text=text,
        page_number=5,
        base_metadata=base_meta,
        chunk_size=500,
        chunk_overlap=50,
    )

    assert len(chunks) >= 2
    for c in chunks:
        assert c["metadata"]["page"] == 5
        assert c["metadata"]["crop"] == "rice"
        assert len(c["text"]) <= 600


def test_chunk_page_text_filters_short_noise():
    short_noise = "Pg 1"
    chunks = chunk_page_text(
        text=short_noise,
        page_number=1,
        base_metadata={"crop": "cotton"},
        min_chunk_length=40,
    )
    assert len(chunks) == 0

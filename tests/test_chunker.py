"""
Unit tests for text chunker and page boundary preservation.
"""

from app.rag.chunker import chunk_page_text, clean_text, is_chunk_relevant_to_crop


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


def test_chunk_page_text_filters_cross_crop_contamination():
    # A chunk mentioning Maize Fall Armyworm should be rejected if the target crop is groundnut
    faw_maize_text = (
        "Fall army worm in maize: Summer ploughing, collection & destruction of egg masses, "
        "installation of pheromone traps (S. frugiperda) @ 4/acre. Sowing of maize border crop."
    )
    rejected_chunks = chunk_page_text(
        text=faw_maize_text,
        page_number=2,
        base_metadata={"crop": "groundnut", "source": "groundnut_guide.pdf"},
        filter_crop=True,
    )
    assert len(rejected_chunks) == 0

    # A chunk mentioning groundnut should be retained
    groundnut_text = (
        "Groundnut cultivation practices: Farmers are advised to take up summer ploughing and select "
        "high yielding groundnut varieties like TCGS 1694. Suitable time for sowing is July."
    )
    accepted_chunks = chunk_page_text(
        text=groundnut_text,
        page_number=2,
        base_metadata={"crop": "groundnut", "source": "groundnut_guide.pdf"},
        filter_crop=True,
    )
    assert len(accepted_chunks) == 1
    assert accepted_chunks[0]["metadata"]["crop"] == "groundnut"


def test_is_chunk_relevant_to_crop():
    # Valid crop mention
    assert is_chunk_relevant_to_crop("Apply fertilizer to cotton field.", "cotton") is True
    # General guideline without any other crop mention
    assert is_chunk_relevant_to_crop("Deep ploughing and field sanitation are recommended.", "groundnut") is True
    # Contaminated: mentions maize and not groundnut
    assert is_chunk_relevant_to_crop("Control fall armyworm in maize crops.", "groundnut") is False
    # Cross-mention: mentions both groundnut and redgram/maize border
    assert is_chunk_relevant_to_crop("Intercropping groundnut with redgram or maize border crop.", "groundnut") is True

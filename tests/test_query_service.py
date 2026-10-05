"""
Unit tests for deterministic query understanding and context extraction.
"""

from app.services.query_service import query_service


def test_crop_extraction_explicit_overrides_query():
    crop, intent, stage = query_service.extract_context(
        query="Tell me about spraying in maize",
        explicit_crop="cotton"
    )
    assert crop == "cotton"


def test_crop_extraction_from_query_keywords():
    test_cases = [
        ("How to control blast disease in paddy fields?", "rice"),
        ("What is the pink bollworm spray in cotton?", "cotton"),
        ("Spacing recommended for hybrid corn", "maize"),
        ("Tikka disease in groundnut crop", "groundnut"),
        ("Yellow mosaic virus in soybean plants", "soybean"),
    ]
    for q, expected_crop in test_cases:
        crop, _, _ = query_service.extract_context(q)
        assert crop == expected_crop, f"Failed for query: {q}"


def test_intent_classification():
    test_cases = [
        ("How to manage whitefly and thrips?", "pest"),
        ("Leaf blight with brown spots on leaves", "disease"),
        ("How many times should I irrigate during drought?", "irrigation"),
        ("What is the urea and DAP requirement?", "nutrient_management"),
        ("How to control weeds in field?", "weed"),
        ("What is the seed rate and sowing spacing?", "cultivation"),
        ("When to harvest and what is expected yield?", "harvesting"),
    ]
    for q, expected_intent in test_cases:
        _, intent, _ = query_service.extract_context(q)
        assert intent == expected_intent, f"Failed intent for query: {q}"


def test_growth_stage_extraction():
    crop, intent, stage = query_service.extract_context(
        "Severe water stress during flowering stage in cotton",
        explicit_crop="cotton"
    )
    assert crop == "cotton"
    assert intent == "irrigation"
    assert "flowering" in stage.lower()

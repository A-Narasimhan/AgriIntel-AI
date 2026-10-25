"""
Tests for interaction dataset persistence in SQLite.
"""

from pathlib import Path
from app.services.dataset_service import DatasetService
from app.core.schemas import WeatherContext, SourceReference


def test_dataset_log_and_list(tmp_path: Path):
    db_path = tmp_path / "test_interactions.db"
    service = DatasetService(db_path=db_path)

    weather = WeatherContext(
        location="Warangal",
        temperature=28.5,
        humidity=65.0,
        condition="Partly cloudy",
        is_available=True,
    )
    sources = [
        SourceReference(
            source_id="rice_doc.pdf",
            title="Rice Practice",
            crop="rice",
            page=2,
        )
    ]

    service.log_interaction(
        interaction_id="test-uuid-1",
        timestamp="2026-09-30T12:00:00Z",
        query="How to manage blast in rice?",
        crop="rice",
        location="Warangal",
        intent="disease",
        crop_stage="tillering",
        weather=weather,
        advisory="Apply tricyclazole as per ICAR guidelines.",
        evidence_grounded=True,
        sources=sources,
    )

    assert service.count_interactions() == 1
    interactions = service.list_interactions(limit=10)
    assert len(interactions) == 1
    record = interactions[0]
    assert record.interaction_id == "test-uuid-1"
    assert record.crop == "rice"
    assert record.intent == "disease"
    assert record.evidence_grounded is True
    assert record.source_count == 1

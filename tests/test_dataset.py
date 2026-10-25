"""
Comprehensive tests for the interaction dataset persistence, inspection,
and export layer.

All tests use temporary SQLite databases via pytest's tmp_path fixture.
No live API, external LLM, or ChromaDB dependency is required.
"""

import csv
import io
import json
from pathlib import Path

import pytest

from app.services.dataset_service import DatasetService, _safe_parse_sources
from app.core.schemas import WeatherContext, SourceReference


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_service(tmp_path: Path) -> DatasetService:
    """Return a fresh DatasetService backed by a temporary SQLite database."""
    return DatasetService(db_path=tmp_path / "test_interactions.db")


def _make_weather(location: str = "Warangal") -> WeatherContext:
    return WeatherContext(
        location=location,
        temperature=28.5,
        humidity=65.0,
        condition="Partly cloudy",
        is_available=True,
    )


def _make_source(crop: str = "rice") -> SourceReference:
    return SourceReference(
        source_id=f"{crop}_guide.pdf",
        title=f"{crop.title()} Practice Guide",
        crop=crop,
        page=2,
        institution="ICAR",
    )


def _log(
    service: DatasetService,
    interaction_id: str,
    crop: str,
    intent: str = "cultivation",
    evidence_grounded: bool = True,
    timestamp: str = "2026-09-30T12:00:00Z",
    query: str = "Test query",
    location: str = "Warangal",
    sources=None,
) -> None:
    """Convenience wrapper for logging a minimal interaction."""
    service.log_interaction(
        interaction_id=interaction_id,
        timestamp=timestamp,
        query=query,
        crop=crop,
        location=location,
        intent=intent,
        crop_stage="vegetative",
        weather=_make_weather(location),
        advisory=f"Advisory text for {crop}.",
        evidence_grounded=evidence_grounded,
        sources=sources if sources is not None else [_make_source(crop)],
    )


# ---------------------------------------------------------------------------
# Test 1 — List interactions with no filters
# ---------------------------------------------------------------------------

def test_list_no_filters(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "id-1", "rice")
    _log(service, "id-2", "cotton")
    _log(service, "id-3", "maize")

    records = service.list_interactions()
    assert len(records) == 3
    assert service.count_interactions() == 3

    # Every record exposes the expected fields
    for r in records:
        assert r.interaction_id
        assert r.timestamp
        assert r.query
        assert r.crop
        assert isinstance(r.evidence_grounded, bool)
        assert isinstance(r.source_count, int)
        assert isinstance(r.citations, list)


# ---------------------------------------------------------------------------
# Test 2 — Filter by crop (case-insensitive)
# ---------------------------------------------------------------------------

def test_filter_by_crop(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "r1", "rice")
    _log(service, "r2", "rice")
    _log(service, "c1", "cotton")

    records = service.list_interactions(crop="rice")
    assert len(records) == 2
    assert all(r.crop == "rice" for r in records)

    # Case-insensitive
    records_upper = service.list_interactions(crop="RICE")
    assert len(records_upper) == 2

    count = service.count_interactions(crop="rice")
    assert count == 2


# ---------------------------------------------------------------------------
# Test 3 — Filter by intent
# ---------------------------------------------------------------------------

def test_filter_by_intent(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "d1", "rice", intent="disease")
    _log(service, "d2", "cotton", intent="disease")
    _log(service, "p1", "maize", intent="pest")

    records = service.list_interactions(intent="disease")
    assert len(records) == 2
    assert all(r.intent == "disease" for r in records)

    count = service.count_interactions(intent="pest")
    assert count == 1


# ---------------------------------------------------------------------------
# Test 4 — Filter by grounding status
# ---------------------------------------------------------------------------

def test_filter_by_evidence_grounded(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "g1", "rice", evidence_grounded=True)
    _log(service, "g2", "rice", evidence_grounded=True)
    _log(service, "u1", "cotton", evidence_grounded=False)

    grounded = service.list_interactions(evidence_grounded=True)
    ungrounded = service.list_interactions(evidence_grounded=False)

    assert len(grounded) == 2
    assert len(ungrounded) == 1
    assert all(r.evidence_grounded is True for r in grounded)
    assert all(r.evidence_grounded is False for r in ungrounded)


# ---------------------------------------------------------------------------
# Test 5 — Combining multiple filters
# ---------------------------------------------------------------------------

def test_combined_filters(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "a1", "rice", intent="disease", evidence_grounded=True)
    _log(service, "a2", "rice", intent="pest", evidence_grounded=True)
    _log(service, "a3", "cotton", intent="disease", evidence_grounded=True)
    _log(service, "a4", "rice", intent="disease", evidence_grounded=False)

    records = service.list_interactions(crop="rice", intent="disease", evidence_grounded=True)
    assert len(records) == 1
    assert records[0].interaction_id == "a1"

    count = service.count_interactions(crop="rice", intent="disease")
    assert count == 2  # a1 + a4


# ---------------------------------------------------------------------------
# Test 6 — Pagination and invalid pagination parameters
# ---------------------------------------------------------------------------

def test_pagination_and_invalid_params(tmp_path: Path):
    service = _make_service(tmp_path)
    for i in range(10):
        _log(
            service,
            f"pg-{i:02d}",
            "rice",
            timestamp=f"2026-09-{10 + i:02d}T12:00:00Z",
        )

    page1 = service.list_interactions(limit=4, offset=0)
    page2 = service.list_interactions(limit=4, offset=4)
    page3 = service.list_interactions(limit=4, offset=8)

    assert len(page1) == 4
    assert len(page2) == 4
    assert len(page3) == 2

    # No duplicate IDs across pages
    all_ids = [r.interaction_id for r in page1 + page2 + page3]
    assert len(all_ids) == len(set(all_ids))

    # Negative limit/offset clamped internally: limit=0 -> clamped to 1
    clamped = service.list_interactions(limit=0, offset=-5)
    assert len(clamped) >= 1

    # Offset beyond total returns empty list
    beyond = service.list_interactions(limit=10, offset=100)
    assert beyond == []


# ---------------------------------------------------------------------------
# Test 7 — JSONL export with multiple records
# ---------------------------------------------------------------------------

def test_export_jsonl_multiple_records(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "j1", "rice", intent="disease")
    _log(service, "j2", "cotton", intent="pest")

    content = service.export_jsonl()
    lines = [l for l in content.split("\n") if l.strip()]
    assert len(lines) == 2

    for line in lines:
        record = json.loads(line)
        assert "interaction_id" in record
        assert "timestamp" in record
        assert "query" in record
        assert "crop" in record
        assert "advisory" in record
        assert "evidence_grounded" in record
        assert "source_count" in record
        assert "citations" in record
        assert isinstance(record["citations"], list)


# ---------------------------------------------------------------------------
# Test 8 — CSV export: headers and correctly escaped values
# ---------------------------------------------------------------------------

def test_export_csv_headers_and_escaping(tmp_path: Path):
    service = _make_service(tmp_path)

    # Advisory text with commas, quotes, and newlines — all must survive CSV
    tricky_advisory = 'Line 1: "Use pesticide A", B, C.\nLine 2: follow-up.'
    service.log_interaction(
        interaction_id="csv-1",
        timestamp="2026-10-01T10:00:00Z",
        query="How to manage blast?",
        crop="rice",
        location="Warangal",
        intent="disease",
        crop_stage="tillering",
        weather=_make_weather(),
        advisory=tricky_advisory,
        evidence_grounded=True,
        sources=[_make_source("rice")],
    )

    content = service.export_csv()
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    # First row must be the stable header
    expected_headers = [
        "interaction_id", "timestamp", "query", "crop", "location",
        "intent", "crop_stage", "weather_summary", "advisory",
        "evidence_grounded", "source_count", "citations_json",
    ]
    assert rows[0] == expected_headers

    # Only one data row
    assert len(rows) == 2

    data_row = rows[1]
    assert data_row[0] == "csv-1"
    assert data_row[3] == "rice"

    # Advisory round-trips intact (csv module handles quoting)
    assert tricky_advisory in data_row[8]

    # citations_json must be valid JSON
    citations = json.loads(data_row[11])
    assert isinstance(citations, list)
    assert len(citations) == 1


# ---------------------------------------------------------------------------
# Test 9 — Export filters returning only matching records
# ---------------------------------------------------------------------------

def test_export_filters_jsonl(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "f1", "rice", intent="disease", evidence_grounded=True)
    _log(service, "f2", "cotton", intent="disease", evidence_grounded=True)
    _log(service, "f3", "rice", intent="pest", evidence_grounded=False)

    content = service.export_jsonl(crop="rice", intent="disease")
    lines = [l for l in content.split("\n") if l.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["interaction_id"] == "f1"


def test_export_filters_csv(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "e1", "rice", evidence_grounded=True)
    _log(service, "e2", "rice", evidence_grounded=False)
    _log(service, "e3", "cotton", evidence_grounded=True)

    content = service.export_csv(evidence_grounded=False)
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    # 1 header + 1 matching data row
    assert len(rows) == 2
    assert rows[1][0] == "e2"


# ---------------------------------------------------------------------------
# Test 10 — Empty-dataset export
# ---------------------------------------------------------------------------

def test_export_empty_dataset_jsonl(tmp_path: Path):
    service = _make_service(tmp_path)
    content = service.export_jsonl()
    # Empty string or whitespace only — no lines
    assert content.strip() == ""


def test_export_empty_dataset_csv(tmp_path: Path):
    service = _make_service(tmp_path)
    content = service.export_csv()
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    # Header row only, no data rows
    assert len(rows) == 1
    assert rows[0][0] == "interaction_id"


# ---------------------------------------------------------------------------
# Test 11 — Malformed or missing raw_sources_json handled safely
# ---------------------------------------------------------------------------

def test_malformed_sources_json_does_not_crash(tmp_path: Path):
    """Directly insert a row with broken JSON to simulate legacy data."""
    import sqlite3

    service = _make_service(tmp_path)
    db_path = tmp_path / "test_interactions.db"

    conn = sqlite3.connect(str(db_path))
    try:
        with conn:
            conn.execute("""
                INSERT INTO farmer_interactions (
                    interaction_id, timestamp, query, crop, location,
                    intent, crop_stage, weather_summary, advisory,
                    evidence_grounded, source_count, raw_sources_json
                ) VALUES (
                    'bad-json-id', '2026-09-01T00:00:00Z',
                    'Test query', 'rice', NULL,
                    'disease', NULL, NULL, 'Some advisory.',
                    1, 0, 'NOT VALID JSON {{{'
                )
            """)
    finally:
        conn.close()

    # list_interactions must not raise
    records = service.list_interactions()
    assert len(records) == 1
    assert records[0].interaction_id == "bad-json-id"
    assert records[0].citations == []   # malformed -> safe empty list

    # export_jsonl must not raise
    jsonl = service.export_jsonl()
    parsed = json.loads(jsonl.strip())
    assert parsed["citations"] == []

    # export_csv must not raise
    csv_content = service.export_csv()
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    assert len(rows) == 2   # header + 1 data row
    assert json.loads(rows[1][11]) == []


def test_none_sources_json_handled_safely(tmp_path: Path):
    """NULL raw_sources_json (no sources ever logged) must yield empty citations."""
    service = _make_service(tmp_path)

    # Log with empty sources list -> raw_sources_json = "[]"
    service.log_interaction(
        interaction_id="no-src",
        timestamp="2026-09-02T00:00:00Z",
        query="No sources query",
        crop="cotton",
        location=None,
        intent=None,
        crop_stage=None,
        weather=None,
        advisory="Generic advisory.",
        evidence_grounded=False,
        sources=[],
    )

    records = service.list_interactions()
    assert records[0].citations == []
    assert _safe_parse_sources(None) == []
    assert _safe_parse_sources("") == []
    assert _safe_parse_sources("null") == []
    assert _safe_parse_sources('{"key": "val"}') == []  # dict, not list


# ---------------------------------------------------------------------------
# Test 12 — Existing interaction records remain unchanged after export
# ---------------------------------------------------------------------------

def test_export_does_not_mutate_records(tmp_path: Path):
    service = _make_service(tmp_path)
    _log(service, "immutable-1", "rice", intent="disease", evidence_grounded=True)
    _log(service, "immutable-2", "cotton", intent="pest", evidence_grounded=False)

    before = service.list_interactions()
    before_count = service.count_interactions()

    # Trigger both export types
    _ = service.export_jsonl()
    _ = service.export_csv()

    after = service.list_interactions()
    after_count = service.count_interactions()

    assert after_count == before_count
    for b, a in zip(
        sorted(before, key=lambda r: r.interaction_id),
        sorted(after, key=lambda r: r.interaction_id),
    ):
        assert b.interaction_id == a.interaction_id
        assert b.advisory == a.advisory
        assert b.evidence_grounded == a.evidence_grounded
        assert b.citations == a.citations


# ---------------------------------------------------------------------------
# Existing baseline test (preserved)
# ---------------------------------------------------------------------------

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
    assert len(record.citations) == 1
    assert record.citations[0]["title"] == "Rice Practice"

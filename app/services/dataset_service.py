"""
Interaction dataset persistence service using SQLite.

Maintains a structured log of all farmer queries, crop contexts, weather snapshots,
grounded advisories, and source provenances for future evaluation and research.
"""

from typing import List, Optional, Dict, Any
import csv
import io
import json
import sqlite3
from pathlib import Path

from app.core.config import settings
from app.core.schemas import InteractionRecord, WeatherContext, SourceReference

# Maximum rows returned per page to avoid unbounded queries
_MAX_PAGE_SIZE = 200


def _safe_parse_sources(raw_json: Optional[str]) -> List[Dict[str, Any]]:
    """Parse raw_sources_json safely, returning [] on malformed or missing input."""
    if not raw_json:
        return []
    try:
        parsed = json.loads(raw_json)
        if isinstance(parsed, list):
            return parsed
        return []
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


class DatasetService:
    """Manages SQLite storage of farmer interactions."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.sqlite_db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create interactions table and indexes if not already present."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS farmer_interactions (
                        interaction_id TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        query TEXT NOT NULL,
                        crop TEXT NOT NULL,
                        location TEXT,
                        intent TEXT,
                        crop_stage TEXT,
                        weather_summary TEXT,
                        advisory TEXT NOT NULL,
                        evidence_grounded INTEGER NOT NULL,
                        source_count INTEGER NOT NULL,
                        raw_sources_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_crop ON farmer_interactions(crop);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON farmer_interactions(timestamp);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_intent ON farmer_interactions(intent);
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_grounded ON farmer_interactions(evidence_grounded);
                """)
        finally:
            conn.close()

    def log_interaction(
        self,
        interaction_id: str,
        timestamp: str,
        query: str,
        crop: str,
        location: Optional[str],
        intent: Optional[str],
        crop_stage: Optional[str],
        weather: Optional[WeatherContext],
        advisory: str,
        evidence_grounded: bool,
        sources: List[SourceReference],
    ) -> None:
        """Log an advisory interaction into the database."""
        weather_summary = None
        if weather and weather.is_available:
            weather_summary = f"{weather.temperature}°C, {weather.humidity}% hum, {weather.condition}"

        raw_sources = json.dumps([s.model_dump() for s in sources], ensure_ascii=False)

        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO farmer_interactions (
                        interaction_id, timestamp, query, crop, location,
                        intent, crop_stage, weather_summary, advisory,
                        evidence_grounded, source_count, raw_sources_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    interaction_id,
                    timestamp,
                    query,
                    crop,
                    location,
                    intent,
                    crop_stage,
                    weather_summary,
                    advisory,
                    1 if evidence_grounded else 0,
                    len(sources),
                    raw_sources,
                ))
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Internal helper: parameterized filter builder
    # ------------------------------------------------------------------

    def _build_filter_query(
        self,
        crop: Optional[str],
        intent: Optional[str],
        evidence_grounded: Optional[bool],
    ) -> tuple:
        """
        Return (where_clause, params) for the given optional filters.
        All user-supplied values are bound via SQLite parameters — no string
        interpolation of external data ever occurs.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if crop is not None:
            conditions.append("LOWER(crop) = LOWER(?)")
            params.append(crop)
        if intent is not None:
            conditions.append("LOWER(intent) = LOWER(?)")
            params.append(intent)
        if evidence_grounded is not None:
            conditions.append("evidence_grounded = ?")
            params.append(1 if evidence_grounded else 0)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        return where_clause, params

    # ------------------------------------------------------------------
    # Public read API
    # ------------------------------------------------------------------

    def list_interactions(
        self,
        limit: int = 50,
        offset: int = 0,
        crop: Optional[str] = None,
        intent: Optional[str] = None,
        evidence_grounded: Optional[bool] = None,
    ) -> List[InteractionRecord]:
        """
        Fetch logged interactions with optional filters and stable pagination.

        Ordering: newest timestamp first, interaction_id ascending as tie-breaker
        for determinism. Limit is capped at _MAX_PAGE_SIZE.
        """
        limit = min(max(limit, 1), _MAX_PAGE_SIZE)
        offset = max(offset, 0)

        where_clause, params = self._build_filter_query(crop, intent, evidence_grounded)

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT interaction_id, timestamp, query, crop, location,
                       intent, crop_stage, weather_summary, advisory,
                       evidence_grounded, source_count, raw_sources_json
                FROM farmer_interactions
                {where_clause}
                ORDER BY timestamp DESC, interaction_id ASC
                LIMIT ? OFFSET ?
            """, (*params, limit, offset))
            rows = cursor.fetchall()

            return [
                InteractionRecord(
                    interaction_id=row["interaction_id"],
                    timestamp=row["timestamp"],
                    query=row["query"],
                    crop=row["crop"],
                    location=row["location"],
                    intent=row["intent"],
                    crop_stage=row["crop_stage"],
                    weather_summary=row["weather_summary"],
                    advisory=row["advisory"],
                    evidence_grounded=bool(row["evidence_grounded"]),
                    source_count=row["source_count"],
                    citations=_safe_parse_sources(row["raw_sources_json"]),
                )
                for row in rows
            ]
        finally:
            conn.close()

    def count_interactions(
        self,
        crop: Optional[str] = None,
        intent: Optional[str] = None,
        evidence_grounded: Optional[bool] = None,
    ) -> int:
        """Return total logged interactions matching the optional filters."""
        where_clause, params = self._build_filter_query(crop, intent, evidence_grounded)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) FROM farmer_interactions {where_clause}",
                params,
            )
            return cursor.fetchone()[0]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Export helpers — no page-size cap, read-only, never mutate records
    # ------------------------------------------------------------------

    def export_jsonl(
        self,
        crop: Optional[str] = None,
        intent: Optional[str] = None,
        evidence_grounded: Optional[bool] = None,
    ) -> str:
        """
        Return all matching interactions as a JSON Lines string.
        Each line is a self-contained JSON object with all dataset fields.
        Citations are embedded as a JSON array per record.
        Returns an empty string when no records match.
        """
        where_clause, params = self._build_filter_query(crop, intent, evidence_grounded)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT interaction_id, timestamp, query, crop, location,
                       intent, crop_stage, weather_summary, advisory,
                       evidence_grounded, source_count, raw_sources_json
                FROM farmer_interactions
                {where_clause}
                ORDER BY timestamp DESC, interaction_id ASC
            """, params)
            rows = cursor.fetchall()
        finally:
            conn.close()

        lines: List[str] = []
        for row in rows:
            record = {
                "interaction_id": row["interaction_id"],
                "timestamp": row["timestamp"],
                "query": row["query"],
                "crop": row["crop"],
                "location": row["location"],
                "intent": row["intent"],
                "crop_stage": row["crop_stage"],
                "weather_summary": row["weather_summary"],
                "advisory": row["advisory"],
                "evidence_grounded": bool(row["evidence_grounded"]),
                "source_count": row["source_count"],
                "citations": _safe_parse_sources(row["raw_sources_json"]),
            }
            lines.append(json.dumps(record, ensure_ascii=False))
        return "\n".join(lines)

    def export_csv(
        self,
        crop: Optional[str] = None,
        intent: Optional[str] = None,
        evidence_grounded: Optional[bool] = None,
    ) -> str:
        """
        Return all matching interactions as a CSV string with a stable header.
        Multi-line advisory text and JSON citations are safely escaped by the
        csv module (QUOTE_ALL). Returns a header-only CSV when no records match.
        """
        where_clause, params = self._build_filter_query(crop, intent, evidence_grounded)
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT interaction_id, timestamp, query, crop, location,
                       intent, crop_stage, weather_summary, advisory,
                       evidence_grounded, source_count, raw_sources_json
                FROM farmer_interactions
                {where_clause}
                ORDER BY timestamp DESC, interaction_id ASC
            """, params)
            rows = cursor.fetchall()
        finally:
            conn.close()

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\n")

        # Stable header — never reorder these without a schema-version bump
        writer.writerow([
            "interaction_id",
            "timestamp",
            "query",
            "crop",
            "location",
            "intent",
            "crop_stage",
            "weather_summary",
            "advisory",
            "evidence_grounded",
            "source_count",
            "citations_json",
        ])

        for row in rows:
            citations = _safe_parse_sources(row["raw_sources_json"])
            writer.writerow([
                row["interaction_id"],
                row["timestamp"],
                row["query"],
                row["crop"],
                row["location"] or "",
                row["intent"] or "",
                row["crop_stage"] or "",
                row["weather_summary"] or "",
                row["advisory"],
                "true" if row["evidence_grounded"] else "false",
                row["source_count"],
                json.dumps(citations, ensure_ascii=False),
            ])

        return output.getvalue()


# Global instance
dataset_service = DatasetService()

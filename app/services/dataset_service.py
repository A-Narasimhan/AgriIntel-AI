"""
Interaction dataset persistence service using SQLite.

Maintains a structured log of all farmer queries, crop contexts, weather snapshots,
grounded advisories, and source provenances for future evaluation and research.
"""

from typing import List, Optional, Dict, Any
import sqlite3
import json
from pathlib import Path

from app.core.config import settings
from app.core.schemas import InteractionRecord, WeatherContext, SourceReference


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
        """Create interactions table and index if not already present."""
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

    def list_interactions(self, limit: int = 50, offset: int = 0) -> List[InteractionRecord]:
        """Fetch logged interactions with pagination."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT interaction_id, timestamp, query, crop, location,
                       intent, crop_stage, weather_summary, advisory,
                       evidence_grounded, source_count
                FROM farmer_interactions
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
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
                )
                for row in rows
            ]
        finally:
            conn.close()

    def count_interactions(self) -> int:
        """Return total logged interactions."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM farmer_interactions")
            return cursor.fetchone()[0]
        finally:
            conn.close()


# Global instance
dataset_service = DatasetService()

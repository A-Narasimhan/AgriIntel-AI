"""
Pydantic schemas defining data contracts for AgriIntel AI API.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# System & Health
# ---------------------------------------------------------

class HealthResponse(BaseModel):
    """Shape of the response returned by GET /health."""
    status: str = Field(..., description="Current status of the service, e.g. 'ok'.")
    app_name: str = Field(..., description="Name of the application.")
    version: str = Field(..., description="Current application version.")
    environment: str = Field(..., description="Environment the app is running in.")


# ---------------------------------------------------------
# Retrieval
# ---------------------------------------------------------

class RetrievalRequest(BaseModel):
    """Request model for knowledge retrieval."""
    query: str = Field(..., min_length=2, description="Farmer or researcher query.")
    crop: Optional[str] = Field(None, description="Target crop (rice, cotton, maize, groundnut, soybean).")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of chunks to retrieve.")


class RetrievedChunk(BaseModel):
    """A single retrieved evidence chunk with provenance metadata."""
    text: str = Field(..., description="Chunk content.")
    source: str = Field(..., description="Filename or source document identifier.")
    title: str = Field(..., description="Document or section title.")
    crop: str = Field(..., description="Target crop.")
    page: Optional[int] = Field(None, description="Original document page number.")
    year: Optional[int] = Field(None, description="Publication year.")
    topic: Optional[str] = Field(None, description="Agricultural domain/topic.")
    score: Optional[float] = Field(None, description="Relevance score (higher is more similar).")


class RetrievalResponse(BaseModel):
    """Response containing retrieved agricultural evidence."""
    query: str
    crop: Optional[str] = None
    results: List[RetrievedChunk]
    total_found: int


# ---------------------------------------------------------
# Weather
# ---------------------------------------------------------

class WeatherContext(BaseModel):
    """Structured weather information for agricultural context."""
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temperature: Optional[float] = Field(None, description="Current temperature in Celsius.")
    humidity: Optional[float] = Field(None, description="Relative humidity percentage.")
    precipitation: Optional[float] = Field(None, description="Current precipitation in mm.")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h.")
    condition: Optional[str] = Field(None, description="Human-readable weather description.")
    forecast_summary: Optional[str] = Field(None, description="Brief 3-day forecast summary.")
    is_available: bool = Field(default=True, description="Whether live weather was successfully retrieved.")
    note: Optional[str] = Field(None, description="Fallback or status message.")


# ---------------------------------------------------------
# Advisory
# ---------------------------------------------------------

class AdvisoryRequest(BaseModel):
    """Farmer request for agricultural advisory."""
    query: str = Field(..., min_length=2, description="Farmer's query.")
    crop: Optional[str] = Field(None, description="Crop name. If omitted, will be inferred from query.")
    location: Optional[str] = Field(None, description="Location (e.g. Warangal, Hyderabad, Guntur).")
    crop_stage: Optional[str] = Field(None, description="Optional crop growth stage (e.g. vegetative, flowering, boll formation).")


class SourceReference(BaseModel):
    """Attribution citation for grounded evidence."""
    source_id: Optional[str] = None
    title: str
    crop: str
    institution: Optional[str] = None
    page: Optional[int] = None
    year: Optional[int] = None
    excerpt: Optional[str] = None


class AdvisoryResponse(BaseModel):
    """Grounded agricultural advisory response with citations and weather."""
    interaction_id: str
    timestamp: str
    query: str
    crop: str
    location: Optional[str] = None
    intent: str
    crop_stage: Optional[str] = None
    weather: Optional[WeatherContext] = None
    advisory: str
    sources: List[SourceReference]
    evidence_grounded: bool = Field(..., description="True if answer is backed by retrieved knowledge base.")


# ---------------------------------------------------------
# Interaction Dataset & Persistence
# ---------------------------------------------------------

class InteractionRecord(BaseModel):
    """Record representing a logged farmer interaction."""
    interaction_id: str
    timestamp: str
    query: str
    crop: str
    location: Optional[str] = None
    intent: Optional[str] = None
    crop_stage: Optional[str] = None
    weather_summary: Optional[str] = None
    advisory: str
    evidence_grounded: bool
    source_count: int


class InteractionListResponse(BaseModel):
    """List of recorded farmer interactions for dataset analysis."""
    total: int
    interactions: List[InteractionRecord]

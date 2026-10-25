"""
Agricultural advisory, weather, and interaction dataset API routes.
"""

from fastapi import APIRouter, HTTPException, Query, Response
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.core.config import settings
from app.core.schemas import (
    AdvisoryRequest,
    AdvisoryResponse,
    WeatherContext,
    InteractionListResponse,
)
from app.services.query_service import query_service
from app.services.retrieval_service import retrieval_service
from app.services.weather_service import weather_service
from app.services.llm_service import llm_service
from app.services.dataset_service import dataset_service

router = APIRouter(tags=["Advisory & Intelligence"])


@router.post("/advisory", response_model=AdvisoryResponse)
async def generate_advisory(request: AdvisoryRequest) -> AdvisoryResponse:
    """
    Main Agricultural Advisory pipeline:
    1. Validate query and extract crop, intent, crop stage
    2. Retrieve grounded agricultural evidence chunks (RAG)
    3. Retrieve real-time weather and forecast (Open-Meteo)
    4. Generate grounded LLM advisory adhering to anti-hallucination rules
    5. Persist interaction into SQLite interaction dataset
    """
    # 1. Query understanding & context extraction
    detected_crop, intent, detected_stage = query_service.extract_context(
        query=request.query,
        explicit_crop=request.crop,
        explicit_stage=request.crop_stage,
    )

    if not detected_crop:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not identify the target crop. Please specify one of the supported crops: "
                f"{', '.join(settings.supported_crops)}."
            ),
        )

    # 2. Retrieve agricultural evidence chunks from ChromaDB
    chunks = retrieval_service.retrieve(
    query=request.query,
    crop=detected_crop,
    top_k=settings.default_top_k,
    intent=intent,
)

    # 3. Retrieve real-time dynamic weather context
    weather_ctx = await weather_service.get_weather(request.location)

    # 4. Generate grounded advisory via LLM service
    advisory_text, sources, is_grounded = await llm_service.generate_advisory(
        query=request.query,
        crop=detected_crop,
        location=request.location,
        weather=weather_ctx,
        chunks=chunks,
        crop_stage=detected_stage,
        intent=intent,
    )

    # 5. Persist interaction
    interaction_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        dataset_service.log_interaction(
            interaction_id=interaction_id,
            timestamp=timestamp,
            query=request.query,
            crop=detected_crop,
            location=request.location,
            intent=intent,
            crop_stage=detected_stage,
            weather=weather_ctx,
            advisory=advisory_text,
            evidence_grounded=is_grounded,
            sources=sources,
        )
    except Exception as e:
        print(f"Warning: Failed to log interaction to SQLite: {e}")

    return AdvisoryResponse(
        interaction_id=interaction_id,
        timestamp=timestamp,
        query=request.query,
        crop=detected_crop,
        location=request.location,
        intent=intent,
        crop_stage=detected_stage,
        weather=weather_ctx,
        advisory=advisory_text,
        sources=sources,
        evidence_grounded=is_grounded,
    )


@router.get("/weather", response_model=WeatherContext)
async def get_weather_context(
    location: str = Query(..., min_length=2, description="City, town, or district name (e.g. Warangal)")
) -> WeatherContext:
    """
    Fetch real-time agricultural weather and 3-day forecast for a given location.
    """
    return await weather_service.get_weather(location)


@router.get("/interactions/export")
def export_interactions(
    format: str = Query("jsonl", description="Export format: 'jsonl' or 'csv'"),
    crop: Optional[str] = Query(None, description="Filter by crop name (case-insensitive)."),
    intent: Optional[str] = Query(None, description="Filter by detected intent (case-insensitive)."),
    evidence_grounded: Optional[bool] = Query(None, description="Filter by grounding status."),
) -> Response:
    """
    Export logged farmer interactions as JSONL or CSV for dataset evaluation.

    Applies the same crop, intent, and evidence_grounded filters as the
    inspection endpoint. Records are never modified or deleted by this endpoint.

    Supported formats:
    - jsonl: newline-delimited JSON, one record per line
    - csv:   RFC-4180-compatible CSV with a stable header row
    """
    fmt = format.lower().strip()
    if fmt not in ("jsonl", "csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported export format '{format}'. Use 'jsonl' or 'csv'.",
        )

    if fmt == "jsonl":
        content = dataset_service.export_jsonl(
            crop=crop,
            intent=intent,
            evidence_grounded=evidence_grounded,
        )
        return Response(
            content=content,
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": "attachment; filename=\"interactions.jsonl\"",
            },
        )
    else:
        content = dataset_service.export_csv(
            crop=crop,
            intent=intent,
            evidence_grounded=evidence_grounded,
        )
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=\"interactions.csv\"",
            },
        )


@router.get("/interactions", response_model=InteractionListResponse)
def list_logged_interactions(
    limit: int = Query(20, ge=1, le=200, description="Maximum records to return (1–200)."),
    offset: int = Query(0, ge=0, description="Number of records to skip."),
    crop: Optional[str] = Query(None, description="Filter by crop name (case-insensitive)."),
    intent: Optional[str] = Query(None, description="Filter by detected intent (case-insensitive)."),
    evidence_grounded: Optional[bool] = Query(None, description="Filter by grounding status."),
) -> InteractionListResponse:
    """
    Retrieve logged farmer interactions for dataset inspection and research evaluation.

    All filter parameters are optional and combinable. Results are ordered newest
    first with a stable tie-breaker. Pagination metadata (total, limit, offset) is
    always included in the response.
    """
    records = dataset_service.list_interactions(
        limit=limit,
        offset=offset,
        crop=crop,
        intent=intent,
        evidence_grounded=evidence_grounded,
    )
    total = dataset_service.count_interactions(
        crop=crop,
        intent=intent,
        evidence_grounded=evidence_grounded,
    )
    return InteractionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        interactions=records,
    )


@router.get("/crops")
def get_supported_crops():
    """
    List currently supported target crops and configured sources.
    """
    return {
        "supported_crops": settings.supported_crops,
        "total_crops": len(settings.supported_crops),
        "embedding_model": settings.embedding_model_name,
        "chroma_collection": settings.chroma_collection_name,
    }

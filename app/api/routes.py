"""
API routes for AgriIntel AI.

Preserves the GET /health baseline check and mounts the advisory, retrieval,
weather, and dataset endpoints.
"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.schemas import HealthResponse
from app.api.retrieval import router as retrieval_router
from app.api.advisory import router as advisory_router

router = APIRouter()

# Preserve foundational health check
@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """
    Return basic service status.
    Confirms FastAPI process is alive, configured, and responsive.
    """
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )

# Include feature sub-routers
router.include_router(retrieval_router)
router.include_router(advisory_router)

"""
Agricultural knowledge retrieval API routes.
"""

from fastapi import APIRouter, HTTPException
from app.core.schemas import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import retrieval_service

router = APIRouter(prefix="/retrieve", tags=["Knowledge Retrieval"])


@router.post("", response_model=RetrievalResponse)
def retrieve_knowledge(request: RetrievalRequest) -> RetrievalResponse:
    """
    Retrieve domain-specific agricultural evidence chunks from ChromaDB.
    Supports filtering by crop (rice, cotton, maize, groundnut, soybean).
    """
    try:
        results = retrieval_service.retrieve(
            query=request.query,
            crop=request.crop,
            top_k=request.top_k,
        )
        return RetrievalResponse(
            query=request.query,
            crop=request.crop,
            results=results,
            total_found=len(results),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

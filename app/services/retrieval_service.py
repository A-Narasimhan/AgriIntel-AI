"""
Agricultural knowledge retrieval service.
Computes query embeddings and queries ChromaDB with crop-specific metadata filtering.
"""

from typing import List, Optional
from app.core.config import settings
from app.core.schemas import RetrievedChunk
from app.services.embedding_service import embedding_service
from app.rag.vector_store import vector_store
from app.rag.metadata import normalize_crop_name


class RetrievalService:
    """Orchestrates query embedding and vector search with crop filters."""

    def __init__(self):
        self.embedding = embedding_service
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        crop: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant agricultural evidence chunks.
        If crop is specified, retrieval is filtered to only include documents for that crop.
        """
        k = top_k or settings.default_top_k
        normalized_crop = normalize_crop_name(crop)

        # Generate query vector using the same embedding model used for documents
        query_vector = self.embedding.embed_query(query)
        if not query_vector:
            return []

        # Query vector store with crop metadata filter
        results = self.vector_store.search(
            query_embedding=query_vector,
            crop=normalized_crop,
            top_k=k,
        )

        return results


# Global instance
retrieval_service = RetrievalService()

"""
Agricultural knowledge retrieval service.
Computes query embeddings and queries ChromaDB with crop-specific
metadata filtering and optional intent-based evidence filtering.
"""

from typing import List, Optional

from app.core.config import settings
from app.core.schemas import RetrievedChunk
from app.services.embedding_service import embedding_service
from app.rag.vector_store import vector_store
from app.rag.metadata import normalize_crop_name


class RetrievalService:
    """Orchestrates query embedding and crop/intent-filtered retrieval."""

    def __init__(self):
        self.embedding = embedding_service
        self.vector_store = vector_store

    @staticmethod
    def _matches_intent(
        chunk: RetrievedChunk,
        intent: Optional[str],
    ) -> bool:
        """Keep chunks containing terminology related to the requested intent."""

        if not intent or intent == "general":
            return True

        topic = (chunk.topic or "").lower()
        text = chunk.text.lower()
        content = f"{topic} {text}"

        intent_terms = {
            "irrigation": (
                "irrigation", "irrigate", "water management",
                "water level", "moisture", "drip", "drought",
                "water requirement", "water requirements",
            ),
            "pest": (
                "pest", "insect", "bollworm", "whitefly",
                "aphid", "thrips", "jassid", "borer",
            ),
            "disease": (
                "disease", "rot", "blight", "rust", "wilt",
                "mildew", "leaf spot", "tikka", "blast",
            ),
            "nutrient_management": (
                "fertilizer", "fertiliser", "nutrient", "urea",
                "npk", "dap", "potash", "deficiency", "compost",
            ),
            "weed": (
                "weed", "weeding", "herbicide", "weedicide",
            ),
            "cultivation": (
                "sowing", "seed rate", "variety", "spacing",
                "transplanting", "nursery", "land preparation",
            ),
            "harvesting": (
                "harvest", "maturity", "storage", "yield",
            ),
            "weather": (
                "rainfall", "temperature", "weather", "forecast",
                "heat wave", "frost",
            ),
        }

        terms = intent_terms.get(intent)

        # Do not apply an unconfigured filter to an unknown intent.
        if terms is None:
            return True

        return any(term in content for term in terms)

    def retrieve(
        self,
        query: str,
        crop: Optional[str] = None,
        top_k: Optional[int] = None,
        intent: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve crop-specific evidence, optionally filtered by intent.
        """
        k = top_k if top_k is not None else settings.default_top_k
        normalized_crop = normalize_crop_name(crop)

        query_vector = self.embedding.embed_query(query)

        if not query_vector:
            return []

        results = self.vector_store.search(
            query_embedding=query_vector,
            crop=normalized_crop,
            top_k=k,
        )

        return [
            chunk
            for chunk in results
            if self._matches_intent(chunk, intent)
        ]


retrieval_service = RetrievalService()
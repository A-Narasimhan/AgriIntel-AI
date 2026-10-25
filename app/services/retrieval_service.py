"""
Agricultural knowledge retrieval service.
Computes query embeddings and queries ChromaDB with crop-specific
metadata filtering and optional intent-based evidence filtering.
"""

import re
from typing import List, Optional, Tuple

from app.core.config import settings
from app.core.schemas import RetrievedChunk
from app.services.embedding_service import embedding_service
from app.rag.vector_store import vector_store
from app.rag.metadata import normalize_crop_name
from app.services.query_service import query_service


class RetrievalService:
    """Orchestrates query embedding and crop/intent-filtered retrieval."""

    def __init__(self):
        self.embedding = embedding_service
        self.vector_store = vector_store

    @staticmethod
    def _matches_intent(
        chunk: RetrievedChunk,
        intent: Optional[str],
        query: str = "",
    ) -> bool:
        """Keep chunks containing terminology related to the requested intent."""

        if not intent or intent == "general":
            return True

        topic = (chunk.topic or "").lower()
        text = chunk.text.lower()
        content = f"{topic} {text}".replace("_", " ")

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

        if not any(term in content for term in terms):
            return False

        if intent == "disease":
            named_disease_terms = RetrievalService._named_disease_terms(query)
            if named_disease_terms and not RetrievalService._matches_named_disease(
                chunk.text, named_disease_terms
            ):
                return False
            if named_disease_terms and not RetrievalService._has_requested_disease_evidence(
                chunk.text.lower(), query
            ):
                return False
        elif intent == "pest":
            named_pest_terms = RetrievalService._named_pest_terms(query)
            if not named_pest_terms or not any(
                re.search(rf"\b{re.escape(term)}\b", text)
                for term in named_pest_terms
            ):
                return False

        return True

    @staticmethod
    def _named_disease_terms(query: str) -> List[str]:
        """Extract specific disease names so generic disease passages do not fill results."""
        disease_terms = (
            "blast", "tikka", "blight", "rust", "wilt", "mildew", "rot",
            "smut", "anthracnose", "cercospora", "damping off", "leaf spot",
            "brown spot", "leaf curl", "mosaic",
        )
        query_lower = query.lower()
        return [
            term for term in disease_terms
            if re.search(rf"\b{re.escape(term)}\b", query_lower)
        ]

    @staticmethod
    def _named_pest_terms(query: str) -> List[str]:
        pest_terms = (
            "bollworm", "whitefly", "aphid", "thrips", "jassid", "armyworm",
            "stem borer", "borer", "leafhopper", "leaf folder", "caterpillar",
            "mealybug", "mite", "weevil", "beetle", "planthopper", "hopper",
            "bug", "grub", "pink bollworm",
        )
        query_lower = query.lower()
        return [
            term for term in pest_terms
            if re.search(rf"\b{re.escape(term)}\b", query_lower)
        ]

    @staticmethod
    def _relevance_score(chunk: RetrievedChunk, query: str, intent: Optional[str]) -> int:
        """Score disease/task evidence on top of vector similarity."""
        content = chunk.text.lower()
        score = 0
        if intent == "disease":
            named_terms = RetrievalService._named_disease_terms(query)
            score += 20 * sum(
                RetrievalService._matches_named_disease(chunk.text, [term])
                for term in named_terms
            )
            score += 8 * sum(
                term in content
                for term in RetrievalService._disease_task_terms(query)
            )
            score += 4 * sum(
                term in content
                for term in RetrievalService._disease_evidence_terms()
            )
            # Complete passages are preferable to obvious overlap fragments.
            if chunk.text[:1].isupper():
                score += 1
            if chunk.text.rstrip().endswith((".", "!", "?", ":")):
                score += 1
        elif intent == "pest":
            score += 20 * sum(
                bool(re.search(rf"\b{re.escape(term)}\b", content))
                for term in RetrievalService._named_pest_terms(query)
            )
            score += 4 * sum(
                term in content
                for term in (
                    "control", "management", "monitor", "infestation",
                    "spray", "insecticide", "trap", "threshold",
                )
            )
        return score

    @staticmethod
    def _regional_scope(text: str) -> Optional[str]:
        regions = (
            "Jammu & Kashmir", "Jammu and Kashmir", "Telangana", "Andhra Pradesh",
            "Uttar Pradesh", "Uttarakhand", "Punjab", "Karnataka", "Gujarat",
            "Tamil Nadu", "Maharashtra", "Odisha", "Rajasthan", "Kerala",
            "West Bengal", "Bihar", "Chhattisgarh", "Madhya Pradesh",
            "Tripura", "Haryana", "Himachal Pradesh", "Jharkhand",
            "Goa", "Assam", "Arunachal Pradesh", "Manipur", "Meghalaya",
            "Mizoram", "Nagaland", "Sikkim",
        )
        for region in regions:
            if re.search(rf"\b{re.escape(region)}\b", text, re.IGNORECASE):
                return region
        return None

    @staticmethod
    def _location_regions(location: Optional[str]) -> Tuple[str, ...]:
        location_lower = (location or "").lower()
        if "warangal" in location_lower or "telangana" in location_lower:
            return ("Telangana", "Andhra Pradesh")
        if "andhra" in location_lower:
            return ("Andhra Pradesh", "Telangana")
        if "jammu" in location_lower or "kashmir" in location_lower:
            return ("Jammu & Kashmir", "Jammu and Kashmir")
        return ()

    @staticmethod
    def _matches_named_disease(text: str, disease_terms: List[str]) -> bool:
        """Match disease names in passage text, including tikka's leaf-spot synonym."""
        text_lower = text.lower()
        for term in disease_terms:
            if re.search(rf"\b{re.escape(term)}\b", text_lower):
                return True
            if term == "tikka" and re.search(
                r"\b(early|late|groundnut|peanut)?\s*leaf\s*spots?\b",
                text_lower,
            ):
                return True
        return False

    @staticmethod
    def _disease_evidence_terms() -> Tuple[str, ...]:
        return (
            "lesion", "spot", "symptom", "sign", "leaf", "panicle", "neck",
            "seedling", "fungicide", "spray", "treatment", "control",
            "management", "sanitation", "remove infected", "seed treatment",
        )

    @staticmethod
    def _disease_task_terms(query: str) -> Tuple[str, ...]:
        query_lower = query.lower()
        terms: List[str] = []
        if re.search(r"\b(symptom|symptoms|sign|signs|identify|recognize)\b", query_lower):
            terms.extend(("symptom", "symptoms", "sign", "signs", "lesion", "spot", "leaf"))
        if re.search(
            r"\b(control|manage|management|treat|treatment|prevent|prevention|spray|fungicide|remedy)\b",
            query_lower,
        ):
            terms.extend(
                ("control", "manage", "management", "treatment", "prevent",
                 "spray", "fungicide", "sanitation", "seed treatment")
            )
        return tuple(terms)

    @staticmethod
    def _has_requested_disease_evidence(content: str, query: str) -> bool:
        task_terms = RetrievalService._disease_task_terms(query)
        if task_terms:
            return any(term in content for term in task_terms)
        return any(term in content for term in RetrievalService._disease_evidence_terms())

    def retrieve(
        self,
        query: str,
        crop: Optional[str] = None,
        top_k: Optional[int] = None,
        intent: Optional[str] = None,
        location: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """
        Retrieve crop-specific evidence, optionally filtered by intent.
        """
        k = top_k if top_k is not None else settings.default_top_k
        candidate_k = max(k, 20 if intent == "disease" else 10)
        normalized_crop = normalize_crop_name(crop)

        query_vector = self.embedding.embed_query(query)

        if not query_vector:
            return []

        results = self.vector_store.search(
            query_embedding=query_vector,
            crop=normalized_crop,
            top_k=candidate_k,
        )
        for chunk in results:
            chunk.regional_scope = self._regional_scope(chunk.text)

        filtered = [
            chunk
            for chunk in results
            if self._matches_intent(chunk, intent, query)
        ]
        preferred_regions = self._location_regions(location)
        if preferred_regions:
            applicable_exists = any(
                self._regional_scope(chunk.text) is None
                or self._regional_scope(chunk.text) in preferred_regions
                for chunk in filtered
            )
            if applicable_exists:
                filtered = [
                    chunk for chunk in filtered
                    if self._regional_scope(chunk.text) is None
                    or self._regional_scope(chunk.text) in preferred_regions
                ]
        filtered.sort(
            key=lambda chunk: (
                self._relevance_score(chunk, query, intent),
                1 if (
                    not preferred_regions
                    or self._regional_scope(chunk.text) is None
                    or self._regional_scope(chunk.text) in preferred_regions
                ) else 0,
                chunk.score if chunk.score is not None else 0.0,
            ),
            reverse=True,
        )
        return filtered[:k]


retrieval_service = RetrievalService()
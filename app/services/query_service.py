"""
Query understanding and context extraction module.

Deterministically extracts crop, agricultural intent, and crop stage from farmer queries.
Does not introduce complex black-box classifiers or hallucinated entities.
"""

import re
from typing import Optional, Tuple
from app.rag.metadata import normalize_crop_name


CROP_KEYWORD_PATTERNS = {
    "rice": [r"\brice\b", r"\bpaddy\b", r"\bdhan\b"],
    "cotton": [r"\bcotton\b", r"\bkapas\b", r"\bpatti\b"],
    "maize": [r"\bmaize\b", r"\bcorn\b", r"\bmakkai?\b"],
    "groundnut": [r"\bgroundnut\b", r"\bpeanut\b", r"\bmungphali\b"],
    "soybean": [r"\bsoybeans?\b", r"\bsoya\b"],
}

INTENT_KEYWORD_PATTERNS = {
    "pest": [
        r"\bpests?\b", r"\binsects?\b", r"\bbollworms?\b", r"\barmyworms?\b",
        r"\bborers?\b", r"\bwhitefl(y|ies)\b", r"\baphids?\b", r"\bcaterpillars?\b",
        r"\bthrips?\b", r"\bjassids?\b", r"\bplanthoppers?\b", r"\binfestation\b"
    ],
    "disease": [
        r"\bdiseases?\b", r"\bfung(us|al)\b", r"\bblights?\b", r"\bblasts?\b",
        r"\brots?\b", r"\brusts?\b", r"\bspots?\b", r"\bmosaics?\b", r"\bwilts?\b",
        r"\bmildews?\b", r"\byellowing\b", r"\bleaf curl\b", r"\btikka\b"
    ],
    "irrigation": [
        r"\birrigat(e|ion)\b", r"\bwater(ing)?\b", r"\bdrought\b", r"\bmoisture\b",
        r"\bdrip\b", r"\bflooding\b"
    ],
    "nutrient_management": [
        r"\bfertiliz(er|ers)\b", r"\bnutrients?\b", r"\burea\b", r"\bnpk\b",
        r"\bdap\b", r"\bpotash\b", r"\bzinc\b", r"\bcompost\b", r"\bdeficiency\b"
    ],
    "weed": [
        r"\bweeds?\b", r"\bweeding\b", r"\bherbicides?\b", r"\bweedicides?\b"
    ],
    "cultivation": [
        r"\bsow(ing)?\b", r"\bseed rate\b", r"\bvariet(y|ies)\b", r"\bspacing\b",
        r"\btransplanting\b", r"\bnursery\b", r"\bland prep(aration)?\b"
    ],
    "harvesting": [
        r"\bharvest(ing)?\b", r"\byield\b", r"\bmaturity\b", r"\bstorage\b"
    ],
    "weather": [
        r"\brain(fall)?\b", r"\btemperature\b", r"\bfrost\b", r"\bweather\b", r"\bheat wave\b"
    ],
}

STAGE_KEYWORD_PATTERNS = {
    "seedling / nursery": [r"\bseedling\b", r"\bnursery\b", r"\bgermination\b"],
    "vegetative": [r"\bvegetative\b", r"\btillering\b", r"\bbranching\b"],
    "flowering / reproductive": [r"\bflowering\b", r"\bpanicle\b", r"\bsilking\b", r"\bsquaring\b"],
    "boll / pod / grain formation": [r"\bboll formation\b", r"\bpod\b", r"\bgrain filling\b", r"\bpegging\b"],
    "maturity / harvesting": [r"\bmaturity\b", r"\bharvest(ing)?\b", r"\bripening\b"],
}


class QueryUnderstandingService:
    """Extracts agricultural intent, target crop, and growth stage deterministically."""

    def extract_context(
        self,
        query: str,
        explicit_crop: Optional[str] = None,
        explicit_stage: Optional[str] = None,
    ) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Returns (detected_crop, intent, detected_stage).
        """
        # 1. Crop resolution
        crop = normalize_crop_name(explicit_crop)
        if not crop:
            q_lower = query.lower()
            for c_name, patterns in CROP_KEYWORD_PATTERNS.items():
                if any(re.search(pat, q_lower) for pat in patterns):
                    crop = c_name
                    break

        # 2. Intent resolution
        intent = "general"
        q_lower = query.lower()
        for i_name, patterns in INTENT_KEYWORD_PATTERNS.items():
            if any(re.search(pat, q_lower) for pat in patterns):
                intent = i_name
                break

        # 3. Growth stage resolution
        stage = explicit_stage
        if not stage:
            for s_name, patterns in STAGE_KEYWORD_PATTERNS.items():
                if any(re.search(pat, q_lower) for pat in patterns):
                    stage = s_name
                    break

        return crop, intent, stage


query_service = QueryUnderstandingService()

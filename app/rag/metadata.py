"""
Metadata validation and provenance utilities for agricultural chunks.
"""

from typing import Dict, Any, Optional
import hashlib


def normalize_crop_name(crop: Optional[str]) -> Optional[str]:
    """Normalize crop name to canonical lowercase form."""
    if not crop:
        return None
    crop_clean = crop.strip().lower()
    crop_map = {
        "rice": "rice",
        "paddy": "rice",
        "cotton": "cotton",
        "kapas": "cotton",
        "maize": "maize",
        "corn": "maize",
        "groundnut": "groundnut",
        "peanut": "groundnut",
        "soybean": "soybean",
        "soya": "soybean",
        "soya bean": "soybean",
    }
    return crop_map.get(crop_clean, crop_clean)


def create_chunk_id(source: str, page: int, chunk_index: int, text_content: str) -> str:
    """Generate a deterministic, unique chunk ID with readable provenance prefix."""
    # Hash the text to ensure uniqueness even if chunk index collisions occur
    text_hash = hashlib.md5(text_content.encode("utf-8")).hexdigest()[:8]
    clean_source = source.replace(" ", "_").replace(".pdf", "")
    return f"{clean_source}_p{page}_c{chunk_index}_{text_hash}"


def validate_chunk_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all required provenance fields are present and typed correctly for ChromaDB."""
    crop = normalize_crop_name(meta.get("crop", "general"))
    return {
        "crop": crop,
        "source": str(meta.get("source", "unknown")),
        "title": str(meta.get("title", "Agricultural Advisory Document")),
        "institution": str(meta.get("institution", "ICAR")),
        "page": int(meta.get("page", 1)),
        "year": int(meta.get("year", 2024)),
        "topic": str(meta.get("topic", "general_agriculture")),
        "chunk_index": int(meta.get("chunk_index", 0)),
    }

"""
Text chunking module with page boundary and provenance preservation.

Chunking requirements:
- Target size: ~1000 characters
- Target overlap: ~100 characters
- Strict page preservation: chunks do not cross page boundaries so provenance stays accurate.
- Retains paragraph structure and filters meaningless fragments.
"""

import re
from typing import List, Dict, Any, Optional

CROP_ALIASES: Dict[str, List[str]] = {
    "rice": ["rice", "paddy", "oryza"],
    "cotton": ["cotton", "kapas", "gossypium"],
    "maize": ["maize", "corn", "zea mays"],
    "groundnut": ["groundnut", "peanut", "arachis"],
    "soybean": ["soybean", "soya", "glycine max"],
}


def is_chunk_relevant_to_crop(text: str, target_crop: Optional[str]) -> bool:
    """
    Determine if chunk text is relevant to the target crop.
    Rejects chunks that discuss other target crops while having no mention of the target crop,
    preventing cross-crop contamination from multi-crop publications.
    """
    if not target_crop or not text:
        return True

    from app.rag.metadata import normalize_crop_name
    norm_crop = normalize_crop_name(target_crop)
    if not norm_crop or norm_crop not in CROP_ALIASES:
        return True

    text_lower = text.lower()
    target_kws = CROP_ALIASES.get(norm_crop, [norm_crop])
    has_target = any(re.search(rf"\b{re.escape(kw)}\b", text_lower) for kw in target_kws)

    # Check for presence of other supported crops
    other_kws = []
    for c, kws in CROP_ALIASES.items():
        if c != norm_crop:
            other_kws.extend(kws)
    has_other = any(re.search(rf"\b{re.escape(kw)}\b", text_lower) for kw in other_kws)

    # If the chunk explicitly discusses another supported crop and lacks any mention of target crop,
    # it is contaminated cross-crop content.
    if has_other and not has_target:
        return False

    return True


def clean_text(text: str) -> str:
    """Clean extracted PDF text while preserving sentence structure."""
    if not text:
        return ""
    # Replace carriage returns and excessive whitespace
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ consecutive newlines into double newline (paragraphs)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple inline spaces
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_page_text(
    text: str,
    page_number: int,
    base_metadata: Dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    min_chunk_length: int = 40,
    filter_crop: bool = True,
) -> List[Dict[str, Any]]:
    """
    Split text from a single page into overlapping chunks.
    Preserves page boundaries so every chunk can be cited to its exact page.
    Optionally applies crop-specific filtering to eliminate cross-crop contamination.
    """
    cleaned = clean_text(text)
    if len(cleaned) < min_chunk_length:
        return []

    # If the whole page text is within chunk_size, keep it as one chunk
    if len(cleaned) <= chunk_size:
        single_chunk = [{
            "text": cleaned,
            "metadata": {
                **base_metadata,
                "page": page_number,
                "chunk_index": 0,
            }
        }]
        if filter_crop and base_metadata.get("crop"):
            return [
                c for c in single_chunk
                if is_chunk_relevant_to_crop(c["text"], base_metadata.get("crop"))
            ]
        return single_chunk

    # Paragraph-aware chunking
    paragraphs = cleaned.split("\n\n")
    chunks: List[Dict[str, Any]] = []
    current_chunk = ""
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}".strip()
        else:
            if current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "metadata": {
                        **base_metadata,
                        "page": page_number,
                        "chunk_index": chunk_idx,
                    }
                })
                chunk_idx += 1
                # Overlap: keep tail of current_chunk
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else ""
                current_chunk = f"{overlap_text}\n\n{para}".strip()
            else:
                # If a single paragraph exceeds chunk_size, split by sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {sent}".strip()
                    else:
                        if sub_chunk:
                            chunks.append({
                                "text": sub_chunk,
                                "metadata": {
                                    **base_metadata,
                                    "page": page_number,
                                    "chunk_index": chunk_idx,
                                }
                            })
                            chunk_idx += 1
                            overlap_text = sub_chunk[-chunk_overlap:] if len(sub_chunk) > chunk_overlap else ""
                            sub_chunk = f"{overlap_text} {sent}".strip()
                        else:
                            # Hard split if sentence is unusually long
                            chunks.append({
                                "text": sent[:chunk_size],
                                "metadata": {
                                    **base_metadata,
                                    "page": page_number,
                                    "chunk_index": chunk_idx,
                                }
                            })
                            chunk_idx += 1
                            sub_chunk = sent[chunk_size - chunk_overlap:]
                current_chunk = sub_chunk

    if current_chunk and len(current_chunk) >= min_chunk_length:
        chunks.append({
            "text": current_chunk,
            "metadata": {
                **base_metadata,
                "page": page_number,
                "chunk_index": chunk_idx,
            }
        })

    if filter_crop and base_metadata.get("crop"):
        chunks = [
            c for c in chunks
            if is_chunk_relevant_to_crop(c["text"], base_metadata.get("crop"))
        ]
        for idx, c in enumerate(chunks):
            c["metadata"]["chunk_index"] = idx

    return chunks

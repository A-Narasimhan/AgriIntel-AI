"""
RAG core package: text chunking, metadata validation, and persistent vector storage.
"""

from app.rag.chunker import chunk_page_text, clean_text
from app.rag.metadata import create_chunk_id, validate_chunk_metadata, normalize_crop_name
from app.rag.vector_store import vector_store, ChromaVectorStore

__all__ = [
    "chunk_page_text",
    "clean_text",
    "create_chunk_id",
    "validate_chunk_metadata",
    "normalize_crop_name",
    "vector_store",
    "ChromaVectorStore",
]

"""
Persistent ChromaDB vector store wrapper for agricultural knowledge chunks.
Supports crop-specific metadata filtering and provenance preservation.
"""

from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.schemas import RetrievedChunk
from app.rag.metadata import normalize_crop_name


class ChromaVectorStore:
    """Manages persistent ChromaDB vector storage and crop-filtered retrieval."""

    def __init__(self, persist_directory: Optional[str] = None, collection_name: Optional[str] = None):
        self.persist_dir = str(persist_directory or settings.chroma_db_dir)
        self.collection_name = collection_name or settings.chroma_collection_name

        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> int:
        """Add or update chunks in the persistent vector store."""
        if not chunk_ids:
            return 0

        self._collection.upsert(
            ids=chunk_ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunk_ids)

    def search(
        self,
        query_embedding: List[float],
        crop: Optional[str] = None,
        top_k: int = 4,
    ) -> List[RetrievedChunk]:
        """
        Query vector store with optional crop filtering.
        If crop is specified, retrieval is strictly filtered by crop metadata.
        """
        normalized_crop = normalize_crop_name(crop)
        where_filter: Optional[Dict[str, Any]] = None

        if normalized_crop and normalized_crop in settings.supported_crops:
            where_filter = {"crop": normalized_crop}

        # Handle case where collection has fewer elements than top_k
        total_docs = self._collection.count()
        if total_docs == 0:
            return []

        n_results = min(top_k, total_docs)

        query_params: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_params["where"] = where_filter

        results = self._collection.query(**query_params)

        retrieved: List[RetrievedChunk] = []
        if not results or not results.get("documents"):
            return retrieved

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for i, text in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            # For cosine distance, similarity can be estimated as 1 - distance
            dist = distances[i] if i < len(distances) else 1.0
            similarity = round(max(0.0, 1.0 - dist), 4)

            retrieved.append(
                RetrievedChunk(
                    text=text,
                    source=meta.get("source", "unknown"),
                    title=meta.get("title", "Agricultural Advisory Document"),
                    crop=meta.get("crop", "general"),
                    page=meta.get("page"),
                    year=meta.get("year"),
                    topic=meta.get("topic"),
                    score=similarity,
                )
            )

        return retrieved

    def count(self) -> int:
        """Return total number of chunks currently indexed."""
        return self._collection.count()

    def clear(self) -> None:
        """Reset the collection."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )


# Global singleton instance
vector_store = ChromaVectorStore()

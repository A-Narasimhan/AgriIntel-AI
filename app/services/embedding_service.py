"""
Embedding service using sentence-transformers (all-MiniLM-L6-v2).
Implements a lazy-loaded singleton to ensure model weights are loaded once in memory.
"""

from typing import List
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class EmbeddingService:
    """Manages sentence embedding generation using a single shared model instance."""

    def __init__(self, model_name: str = settings.embedding_model_name):
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model on first use."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_query(self, text: str) -> List[float]:
        """Generate normalized embedding vector for a single query."""
        if not text:
            return []
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate batch normalized embeddings for document chunks."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, batch_size=32, normalize_embeddings=True)
        return embeddings.tolist()


# Global singleton instance
embedding_service = EmbeddingService()

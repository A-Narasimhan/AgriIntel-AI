"""Focused tests for candidate-pool expansion and intent-grounded retrieval."""

from app.core.schemas import RetrievedChunk
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService


class _FakeEmbedding:
    def embed_query(self, query):
        return [0.1, 0.2]


class _FakeVectorStore:
    def __init__(self, candidates):
        self.candidates = candidates
        self.search_kwargs = None

    def search(self, **kwargs):
        self.search_kwargs = kwargs
        return self.candidates[:kwargs["top_k"]]


def _chunk(text, topic=None):
    return RetrievedChunk(
        text=text,
        source="cotton_guide.pdf",
        title="Cotton Guide",
        crop="cotton",
        topic=topic,
    )


def _retrieval_service(candidates):
    service = RetrievalService()
    service.embedding = _FakeEmbedding()
    vector_store = _FakeVectorStore(candidates)
    service.vector_store = vector_store
    return service, vector_store


def test_retrieval_requests_at_least_ten_candidates():
    service, vector_store = _retrieval_service([])

    service.retrieve("cotton irrigation", crop="cotton", top_k=3, intent="irrigation")

    assert vector_store.search_kwargs["top_k"] == 10
    assert vector_store.search_kwargs["crop"] == "cotton"


def test_retrieval_returns_no_more_than_requested_top_k():
    candidates = [_chunk(f"Cotton irrigation at flowering; evidence {index}.") for index in range(10)]
    service, _ = _retrieval_service(candidates)

    results = service.retrieve("cotton irrigation", crop="cotton", top_k=2, intent="irrigation")

    assert len(results) == 2


def test_cotton_irrigation_evidence_in_expanded_candidates_survives_filtering():
    candidates = [
        _chunk(f"Cotton variety selection evidence {index}.", topic="cultivation")
        for index in range(9)
    ]
    relevant = _chunk(
        "Cotton irrigation during flowering is important to avoid water stress.",
        topic="irrigation",
    )
    candidates.append(relevant)
    service, vector_store = _retrieval_service(candidates)

    results = service.retrieve("cotton irrigation", crop="cotton", top_k=2, intent="irrigation")

    assert vector_store.search_kwargs["top_k"] == 10
    assert results == [relevant]
    assert LLMService._has_relevant_evidence("cotton irrigation during flowering", results)


def test_non_irrigation_text_is_rejected_by_existing_grounding_safeguard():
    irrelevant_chunks = [
        _chunk("Apply nitrogen fertilizer and urea to support cotton growth.", topic="fertilizer"),
        _chunk("Select cotton varieties suitable for the flowering stage.", topic="cultivation"),
    ]

    for chunk in irrelevant_chunks:
        assert not LLMService._has_relevant_evidence(
            "What irrigation is needed for cotton?", [chunk]
        )

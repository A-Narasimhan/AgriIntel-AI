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


def _chunk(text, topic=None, crop="cotton"):
    return RetrievedChunk(
        text=text,
        source="cotton_guide.pdf",
        title="Cotton Guide",
        crop=crop,
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


def test_named_disease_evidence_is_ranked_and_generic_disease_text_is_excluded():
    candidates = [
        _chunk(
            "Rice seed treatment and general cultivation practices reduce disease risk.",
            topic="disease",
        ),
        _chunk(
            "Jammu and Kashmir rice varieties are selected for local conditions.",
            topic="cultivation",
            crop="rice",
        ),
        _chunk(
            "Blast disease causes lesions; manage blast with field sanitation and a recommended fungicide.",
            topic="disease management",
        ),
    ]
    service, vector_store = _retrieval_service(candidates)

    results = service.retrieve(
        "How to control blast disease in paddy fields?",
        crop="rice",
        top_k=3,
        intent="disease",
    )

    assert vector_store.search_kwargs["crop"] == "rice"
    assert [chunk.text for chunk in results] == [candidates[2].text]


def test_named_disease_grounding_rejects_other_disease_evidence():
    generic_chunk = _chunk(
        "Rice seed treatment helps prevent disease and supports healthy cultivation.",
        topic="disease management",
    )
    assert not LLMService._has_relevant_evidence(
        "How to control blast disease in paddy fields?",
        [generic_chunk],
        intent="disease",
        crop="rice",
    )


def test_rice_blast_retrieval_prefers_symptoms_and_control_over_generic_context():
    candidates = [
        _chunk(
            "Jammu and Kashmir rice varieties are selected for local conditions.",
            topic="cultivation",
        ),
        _chunk(
            "Rice seedling diseases are reduced through good nursery hygiene.",
            topic="disease",
            crop="rice",
        ),
        _chunk(
            "Rice blast symptoms include spindle-shaped lesions on leaves and necks. "
            "For blast control, remove infected debris and use the recommended fungicide.",
            topic="disease management",
            crop="rice",
        ),
    ]
    service, _ = _retrieval_service(candidates)

    results = service.retrieve(
        "What are rice blast symptoms and how can I control blast?",
        crop="rice",
        top_k=4,
        intent="disease",
    )

    assert [chunk.text for chunk in results] == [candidates[2].text]
    assert LLMService._has_relevant_evidence(
        "What are rice blast symptoms and how can I control blast?",
        results,
        intent="disease",
        crop="rice",
    )


def test_groundnut_tikka_retrieval_requires_tikka_evidence():
    candidates = [
        _chunk(
            "Groundnut varieties should be selected for the local growing season.",
            topic="cultivation",
            crop="groundnut",
        ),
        _chunk(
            "Tikka disease causes dark brown circular leaf spots. "
            "Control it with field sanitation and the recommended fungicide.",
            topic="disease management",
            crop="groundnut",
        ),
        _chunk(
            "Groundnut irrigation should be scheduled during pod development.",
            topic="irrigation",
            crop="groundnut",
        ),
    ]
    service, _ = _retrieval_service(candidates)

    results = service.retrieve(
        "How do I identify and control tikka disease in groundnut?",
        crop="groundnut",
        top_k=4,
        intent="disease",
    )

    assert [chunk.text for chunk in results] == [candidates[1].text]
    assert LLMService._has_relevant_evidence(
        "How do I identify and control tikka disease in groundnut?",
        results,
        intent="disease",
        crop="groundnut",
    )


def test_tikka_topic_metadata_does_not_make_a_table_of_contents_relevant():
    table_of_contents = _chunk(
        "Foliar Disease Management Module for Groundnut. Contents: pages 19-24.",
        topic="pest_management, tikka_disease, disease_control",
        crop="groundnut",
    )

    service, _ = _retrieval_service([table_of_contents])
    results = service.retrieve(
        "How do I identify and control tikka disease in groundnut?",
        crop="groundnut",
        top_k=4,
        intent="disease",
    )

    assert results == []


def test_disease_candidate_pool_expands_for_lower_ranked_specific_evidence():
    candidates = [
        _chunk(f"Groundnut varieties and general disease context {index}.", topic="disease", crop="groundnut")
        for index in range(19)
    ]
    candidates.append(
        _chunk(
            "Early leaf spot symptoms appear as lesions. Apply the recommended fungicide for control.",
            topic="tikka_disease, disease_control",
            crop="groundnut",
        )
    )
    service, vector_store = _retrieval_service(candidates)

    results = service.retrieve(
        "How do I identify and control tikka disease in groundnut?",
        crop="groundnut",
        top_k=4,
        intent="disease",
    )

    assert vector_store.search_kwargs["top_k"] == 20
    assert len(results) == 1
    assert "Early leaf spot" in results[0].text


def test_broad_pest_query_excludes_crop_metadata_only_passages():
    candidates = [
        _chunk(
            "Cotton sowing dates and moisture conservation practices.",
            topic="pest_management",
        ),
        _chunk(
            "Cotton seed treatment and weed control recommendations.",
            topic="pest_management",
        ),
    ]
    service, _ = _retrieval_service(candidates)

    results = service.retrieve(
        "How to manage a cotton pest?",
        crop="cotton",
        top_k=4,
        intent="pest",
    )

    assert results == []
    assert not LLMService._has_relevant_evidence(
        "How to manage a cotton pest?",
        candidates,
        intent="pest",
        crop="cotton",
    )


def test_disease_display_evidence_excludes_named_but_task_irrelevant_passages():
    blast_context = _chunk(
        "Rice blast is common in some rice-growing areas.",
        topic="disease management",
        crop="rice",
    )
    blast_management = _chunk(
        "Rice blast can be controlled with field sanitation and the recommended fungicide.",
        topic="disease management",
        crop="rice",
    )

    assert not LLMService._chunk_supports_disease_aspect(
        blast_context.text,
        "How to manage blast disease in rice",
    )
    assert LLMService._chunk_supports_disease_aspect(
        blast_management.text,
        "How to manage blast disease in rice",
    )


def test_warangal_prefers_general_or_local_blast_evidence_over_jammu_guidance():
    candidates = [
        _chunk(
            "Jammu and Kashmir fungicidal management: blast control requires scheduled sprays.",
            topic="disease management",
            crop="rice",
        ),
        _chunk(
            "Rice blast management in India includes field sanitation and recommended fungicide use.",
            topic="disease management",
            crop="rice",
        ),
    ]
    service, _ = _retrieval_service(candidates)

    results = service.retrieve(
        "How to manage blast disease in rice",
        crop="rice",
        top_k=4,
        intent="disease",
        location="Warangal",
    )

    assert len(results) == 1
    assert results[0].regional_scope is None


def test_region_scope_is_preserved_for_source_labeling():
    chunk = _chunk(
        "Jammu and Kashmir fungicidal management: blast control requires scheduled sprays.",
        topic="disease management",
        crop="rice",
    )
    service, _ = _retrieval_service([chunk])

    results = service.retrieve(
        "How to manage blast disease in rice",
        crop="rice",
        top_k=4,
        intent="disease",
    )

    assert results[0].regional_scope == "Jammu and Kashmir"


def test_combined_disease_query_is_ungrounded_when_only_symptoms_are_supported():
    symptoms_only = _chunk(
        "Rice blast symptoms include spindle-shaped lesions on leaves and necks.",
        topic="disease",
        crop="rice",
    )

    assert not LLMService._has_relevant_evidence(
        "What are rice blast symptoms and how can I control blast?",
        [symptoms_only],
        intent="disease",
        crop="rice",
    )


def test_combined_disease_query_can_combine_separate_symptom_and_management_chunks():
    chunks = [
        _chunk(
            "Rice blast symptoms include spindle-shaped lesions on leaves and necks.",
            topic="disease",
            crop="rice",
        ),
        _chunk(
            "For rice blast control, remove infected debris and use the recommended fungicide.",
            topic="disease management",
            crop="rice",
        ),
    ]

    assert LLMService._has_relevant_evidence(
        "What are rice blast symptoms and how can I control blast?",
        chunks,
        intent="disease",
        crop="rice",
    )

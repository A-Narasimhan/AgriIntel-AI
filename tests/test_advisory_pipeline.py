"""
Integration tests for the Advisory and System API endpoints.
"""

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.schemas import RetrievedChunk, WeatherContext

client = TestClient(app)


def test_get_crops_returns_five_crops():
    response = client.get("/crops")
    assert response.status_code == 200
    data = response.json()
    assert "supported_crops" in data
    assert len(data["supported_crops"]) == 5
    assert set(data["supported_crops"]) == {"rice", "cotton", "maize", "groundnut", "soybean"}


def test_advisory_pipeline_with_explicit_crop():
    payload = {
        "query": "What is the recommended irrigation schedule during dry spells?",
        "crop": "cotton",
        "location": "Warangal",
    }
    response = client.post("/advisory", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["crop"] == "cotton"
    assert data["location"] == "Warangal"
    assert data["intent"] == "irrigation"
    assert "interaction_id" in data
    assert "advisory" in data
    assert "weather" in data
    assert isinstance(data["sources"], list)


def test_advisory_pipeline_infers_crop_from_query():
    payload = {
        "query": "How to manage stem rot disease in groundnut fields?",
        "location": "Guntur",
    }
    response = client.post("/advisory", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["crop"] == "groundnut"
    assert data["intent"] == "disease"


def test_advisory_pipeline_requires_crop_if_unidentifiable():
    payload = {
        "query": "What should I do about the yellow leaves?",
    }
    response = client.post("/advisory", json=payload)
    assert response.status_code == 400
    assert "Could not identify the target crop" in response.json()["detail"]


def test_advisory_pipeline_rejects_selected_crop_conflict():
    payload = {
        "query": "What are the symptoms of blast disease in groundnut and how can I manage it?",
        "crop": "soybean",
    }
    with patch("app.api.advisory.weather_service.get_weather", AsyncMock()) as weather, \
         patch("app.api.advisory.retrieval_service.retrieve") as retrieve:
        response = client.post("/advisory", json=payload)

    assert response.status_code == 400
    assert "conflicts" in response.json()["detail"]
    weather.assert_not_awaited()
    retrieve.assert_not_called()


def test_interactions_endpoint():
    response = client.get("/interactions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "interactions" in data
    assert isinstance(data["interactions"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0


@pytest.fixture
def mock_weather():
    return WeatherContext(
        location="Indore",
        temperature=28.0,
        humidity=60.0,
        precipitation=0.0,
        wind_speed=10.0,
        condition="Clear sky",
        forecast_summary="3-Day Outlook: Dry conditions expected.",
        is_available=True,
    )


def test_advisory_pipeline_soybean_cultivation_with_relevant_evidence(mock_weather):
    relevant_chunk = RetrievedChunk(
        text="Recommended seed rate for soybean is 65-75 kg/ha with row-to-row spacing of 45 cm for optimum plant population.",
        source="soybean_cultivation_guide.pdf",
        title="Soybean Cultivation Guide",
        crop="soybean",
        page=12,
        topic="cultivation",
    )
    payload = {
        "query": "What is the recommended seed rate and spacing for soybean?",
        "crop": "soybean",
        "location": "Indore",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[relevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "soybean"
    assert data["intent"] == "cultivation"
    assert data["evidence_grounded"] is True
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "soybean_cultivation_guide.pdf"
    assert "Soybean Cultivation Guide" in data["advisory"]


def test_advisory_pipeline_weed_management_with_relevant_evidence(mock_weather):
    relevant_chunk = RetrievedChunk(
        text="Apply atrazine at 1.0 kg/ha as pre-emergence herbicide spray for effective weed management in maize.",
        source="maize_production.pdf",
        title="Maize Production Guide",
        crop="maize",
        page=7,
        topic="weed",
    )
    payload = {
        "query": "How to control weeds in maize field?",
        "crop": "maize",
        "location": "Warangal",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[relevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "maize"
    assert data["intent"] == "weed"
    assert data["evidence_grounded"] is True
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "maize_production.pdf"
    assert "Maize Production Guide" in data["advisory"]


def test_advisory_pipeline_nutrient_management_with_relevant_evidence(mock_weather):
    relevant_chunk = RetrievedChunk(
        text="Recommended fertilizer application dose for rice is 120 kg nitrogen, 60 kg P2O5 as DAP, and 40 kg potash per hectare.",
        source="rice_manual.pdf",
        title="Rice Production Manual",
        crop="rice",
        page=15,
        topic="nutrient_management",
    )
    payload = {
        "query": "What is the recommended urea and DAP fertilizer dose for rice?",
        "crop": "rice",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[relevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "rice"
    assert data["intent"] == "nutrient_management"
    assert data["evidence_grounded"] is True
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "rice_manual.pdf"
    assert "Rice Production Manual" in data["advisory"]


def test_advisory_pipeline_irrelevant_evidence_rejected(mock_weather):
    irrelevant_chunk = RetrievedChunk(
        text="Apply chlorantraniliprole 18.5 SC at 150 ml/ha to manage bollworm larvae in cotton fields.",
        source="cotton_pest.pdf",
        title="Cotton Pest Management",
        crop="cotton",
        page=20,
        topic="pest",
    )
    payload = {
        "query": "What is the recommended sowing time and spacing for cotton?",
        "crop": "cotton",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[irrelevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "cotton"
    assert data["intent"] == "cultivation"
    assert data["evidence_grounded"] is False
    assert len(data["sources"]) == 0
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_crop_stage_context_in_synthesis(mock_weather):
    relevant_chunk = RetrievedChunk(
        text="In soybean, vegetative stage requires weed-free conditions and optimum spacing of 45 cm for plant development.",
        source="soybean_cultivation_guide.pdf",
        title="Soybean Cultivation Guide",
        crop="soybean",
        page=14,
        topic="cultivation",
    )
    payload = {
        "query": "What is the recommended spacing for soybean?",
        "crop": "soybean",
        "crop_stage": "vegetative",
        "location": "Indore",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[relevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["crop_stage"] == "vegetative"
    assert data["evidence_grounded"] is True
    assert "Observed Crop Growth Stage" in data["advisory"]
    assert "Vegetative" in data["advisory"]


def test_advisory_pipeline_provenance_only_relevant_sources_cited(mock_weather):
    relevant_chunk = RetrievedChunk(
        text="Recommended seed rate for soybean is 65-75 kg/ha with row-to-row spacing of 45 cm for optimum plant population.",
        source="soybean_cultivation_guide.pdf",
        title="Soybean Cultivation Guide",
        crop="soybean",
        page=12,
        topic="cultivation",
    )
    irrelevant_chunk = RetrievedChunk(
        text="Apply chlorantraniliprole 18.5 SC at 150 ml/ha to manage bollworm larvae in cotton fields.",
        source="cotton_pest.pdf",
        title="Cotton Pest Management",
        crop="soybean",
        page=20,
        topic="pest",
    )
    payload = {
        "query": "What is the recommended seed rate and spacing for soybean?",
        "crop": "soybean",
        "location": "Indore",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[relevant_chunk, irrelevant_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_grounded"] is True
    # Provenance: only the relevant source actually used should be returned
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "soybean_cultivation_guide.pdf"
    assert "Cotton Pest Management" not in data["advisory"]
    assert "chlorantraniliprole" not in data["advisory"]


def test_advisory_pipeline_negative_pest_infestation_rejected_for_weed_query(mock_weather):
    # Misleading chunk mentioning "infestation" and "control" for an insect pest, not a weed
    pest_chunk = RetrievedChunk(
        text="Fall armyworm causes severe insect infestation in maize. Spray chlorantraniliprole for chemical control.",
        source="maize_pest.pdf",
        title="Maize Pest Management",
        crop="maize",
        page=5,
        topic="pest",
    )
    payload = {
        "query": "How to control weeds in maize field?",
        "crop": "maize",
        "location": "Warangal",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[pest_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "weed"
    assert data["evidence_grounded"] is False
    assert len(data["sources"]) == 0
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_negative_spotted_bollworm_rejected_for_disease_query(mock_weather):
    # Insect pest chunk containing "spotted" should not be treated as a disease "spot"
    pest_chunk = RetrievedChunk(
        text="Spotted bollworm larvae bore into cotton bolls. Apply indoxacarb spray for insect control.",
        source="cotton_insects.pdf",
        title="Cotton Insect Guide",
        crop="cotton",
        page=11,
        topic="pest",
    )
    payload = {
        "query": "How to control leaf blight fungal disease in cotton?",
        "crop": "cotton",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[pest_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "disease"
    assert data["evidence_grounded"] is False
    assert len(data["sources"]) == 0
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_named_disease_without_matching_evidence_is_ungrounded(mock_weather):
    generic_disease_chunk = RetrievedChunk(
        text="Rice seed treatment helps prevent disease and supports healthy cultivation.",
        source="rice_cultivation.pdf",
        title="Rice Cultivation Guide",
        crop="rice",
        page=6,
        topic="disease management",
    )
    payload = {
        "query": "How to control blast disease in paddy fields?",
        "crop": "rice",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[generic_disease_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_grounded"] is False
    assert data["sources"] == []
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_combined_disease_query_requires_symptoms_and_management(mock_weather):
    symptoms_only = RetrievedChunk(
        text="Rice blast symptoms include spindle-shaped lesions on leaves and necks.",
        source="rice_disease.pdf",
        title="Rice Disease Guide",
        crop="rice",
        page=7,
        topic="disease",
    )
    payload = {
        "query": "What are rice blast symptoms and how can I control blast?",
        "crop": "rice",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[symptoms_only]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_grounded"] is False
    assert data["sources"] == []
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_broad_pest_query_asks_for_specific_pest(mock_weather):
    generic_chunks = [
        RetrievedChunk(
            text="Cotton sowing dates and moisture conservation practices.",
            source="cotton_guide.pdf",
            title="Cotton Guide",
            crop="cotton",
            page=4,
            topic="pest_management",
        ),
        RetrievedChunk(
            text="Cotton seed treatment and weed control recommendations.",
            source="cotton_guide.pdf",
            title="Cotton Guide",
            crop="cotton",
            page=5,
            topic="pest_management",
        ),
    ]
    payload = {
        "query": "How to manage a cotton pest?",
        "crop": "cotton",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=generic_chunks):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_grounded"] is False
    assert data["sources"] == []
    assert "identify the specific cotton pest" in data["advisory"].lower()


def test_advisory_pipeline_warangal_does_not_present_jammu_blast_as_local(mock_weather):
    regional_chunk = RetrievedChunk(
        text="Jammu and Kashmir fungicidal management: blast control requires scheduled sprays.",
        source="rice_production_and_protection.pdf",
        title="ICAR Rice Guide",
        crop="rice",
        page=33,
        topic="disease_management",
        regional_scope="Jammu and Kashmir",
    )
    payload = {
        "query": "How to manage blast disease in rice",
        "crop": "rice",
        "location": "Warangal",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[regional_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["evidence_grounded"] is False
    assert data["sources"] == []
    assert "locally applicable" in data["advisory"].lower()


def test_advisory_pipeline_negative_yield_loss_rejected_for_harvesting_query(mock_weather):
    # Pest chunk mentioning yield loss should not be accepted as harvesting evidence
    pest_chunk = RetrievedChunk(
        text="Pink bollworm infestation causes 40% yield loss in cotton at boll development stage. Spray profenofos.",
        source="cotton_pests.pdf",
        title="Cotton Pest Guide",
        crop="cotton",
        page=8,
        topic="pest",
    )
    payload = {
        "query": "When should I harvest cotton crop?",
        "crop": "cotton",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[pest_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "harvesting"
    assert data["evidence_grounded"] is False
    assert len(data["sources"]) == 0
    assert "Reliable supporting information was not found" in data["advisory"]


def test_advisory_pipeline_weather_intent_with_relevant_evidence(mock_weather):
    weather_chunk = RetrievedChunk(
        text="In case of heavy rainfall forecast, postpone chemical spray and ensure proper field drainage to avoid waterlogging.",
        source="weather_advisory_guide.pdf",
        title="Agricultural Weather Advisory Guide",
        crop="cotton",
        page=3,
        topic="weather",
    )
    payload = {
        "query": "What weather precautions should be taken for cotton during rainfall?",
        "crop": "cotton",
        "location": "Warangal",
    }

    with patch("app.api.advisory.weather_service.get_weather", AsyncMock(return_value=mock_weather)), \
         patch("app.api.advisory.retrieval_service.retrieve", return_value=[weather_chunk]):
        response = client.post("/advisory", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "weather"
    assert data["evidence_grounded"] is True
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_id"] == "weather_advisory_guide.pdf"


def test_intent_normalization_and_fallback_behavior():
    from app.services.llm_service import LLMService

    fertilizer_chunk = RetrievedChunk(
        text="Apply urea at 100 kg/ha as top dressing fertilizer dose for rice.",
        source="fertilizer_guide.pdf",
        title="Fertilizer Guide",
        crop="rice",
        page=4,
        topic="nutrient_management",
    )

    # 1. intent="nutrient" normalizes to nutrient_management
    assert LLMService._has_relevant_evidence(
        query="What is the dose?",
        chunks=[fertilizer_chunk],
        intent="nutrient",
    ) is True

    # 2. intent="general" falls back to query keywords
    assert LLMService._has_relevant_evidence(
        query="What fertilizer dose should I apply?",
        chunks=[fertilizer_chunk],
        intent="general",
    ) is True

    # 3. intent=None falls back to query keywords
    assert LLMService._has_relevant_evidence(
        query="What fertilizer dose should I apply?",
        chunks=[fertilizer_chunk],
        intent=None,
    ) is True

    # 4. Unknown intent and non-matching query rejects evidence
    assert LLMService._has_relevant_evidence(
        query="Tell me something random about rice",
        chunks=[fertilizer_chunk],
        intent=None,
    ) is False

"""
Integration tests for the Advisory and System API endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

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


def test_interactions_endpoint():
    response = client.get("/interactions?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "interactions" in data
    assert isinstance(data["interactions"], list)

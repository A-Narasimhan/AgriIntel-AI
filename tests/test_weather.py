"""
Unit and integration tests for Open-Meteo weather service.
"""

import pytest
from app.services.weather_service import weather_service, WMO_CODE_MAP


@pytest.mark.anyio
async def test_weather_empty_location_returns_fallback():
    weather = await weather_service.get_weather("")
    assert weather.is_available is False
    assert "No location provided" in weather.note


@pytest.mark.anyio
async def test_weather_invalid_location_handles_gracefully():
    weather = await weather_service.get_weather("NonExistentPlaceXYZ987654321")
    assert weather.is_available is False
    assert "Could not locate" in weather.note


def test_wmo_code_mapping_completeness():
    assert WMO_CODE_MAP[0] == "Clear sky"
    assert "rain" in WMO_CODE_MAP[61].lower()
    assert "thunderstorm" in WMO_CODE_MAP[95].lower()


def test_forecast_summary_generator():
    daily_mock = {
        "time": ["2026-10-01", "2026-10-02", "2026-10-03"],
        "precipitation_sum": [0.0, 1.2, 0.0],
        "temperature_2m_max": [32.5, 31.0, 33.0],
        "temperature_2m_min": [22.0, 21.5, 23.0],
    }
    summary = weather_service._summarize_forecast(daily_mock)
    assert "3-Day Outlook" in summary
    assert "Temp range" in summary

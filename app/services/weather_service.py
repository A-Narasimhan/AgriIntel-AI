"""
Weather service using Open-Meteo API and httpx.

Retrieves real-time agricultural weather and 3-day forecast based on location.
Distinguishes dynamic weather from static agricultural knowledge base evidence.
Handles timeouts, connection errors, and invalid locations gracefully without crashing.
"""

from typing import Optional, Dict, Any, Tuple
import httpx

from app.core.config import settings
from app.core.schemas import WeatherContext


# WMO Weather interpretation codes (WW)
WMO_CODE_MAP: Dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class WeatherService:
    """Manages geocoding and weather retrieval using Open-Meteo public endpoints."""

    def __init__(self, timeout: float = settings.weather_timeout_seconds):
        self.timeout = timeout

    async def get_coordinates(self, location_name: str) -> Optional[Tuple[float, float, str]]:
        """
        Geocode location name using Open-Meteo Geocoding API.
        Returns (latitude, longitude, resolved_name) or None.
        """
        if not location_name or not location_name.strip():
            return None

        params = {
            "name": location_name.strip(),
            "count": 1,
            "language": "en",
            "format": "json"
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(settings.weather_geocoding_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results")
                    if results and len(results) > 0:
                        first = results[0]
                        lat = float(first["latitude"])
                        lon = float(first["longitude"])
                        resolved = f"{first.get('name', location_name)}, {first.get('admin1', '')} {first.get('country', '')}".strip()
                        return lat, lon, resolved
        except Exception as e:
            # Non-blocking log
            print(f"Weather geocoding error for '{location_name}': {e}")

        return None

    async def get_weather(self, location_name: Optional[str]) -> WeatherContext:
        """
        Fetch real-time weather and forecast for agricultural advisory.
        Always returns a valid WeatherContext, even on network/API failure.
        """
        if not location_name or not location_name.strip():
            return WeatherContext(
                location="Not specified",
                is_available=False,
                note="No location provided. Weather-specific advisory was not applied."
            )

        coords = await self.get_coordinates(location_name)
        if not coords:
            return WeatherContext(
                location=location_name,
                is_available=False,
                note=f"Could not locate '{location_name}'. Weather information is currently unavailable."
            )

        lat, lon, resolved_name = coords

        forecast_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "auto",
            "forecast_days": 3,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(settings.weather_forecast_url, params=forecast_params)
                if resp.status_code != 200:
                    return WeatherContext(
                        location=resolved_name,
                        latitude=lat,
                        longitude=lon,
                        is_available=False,
                        note=f"Weather API returned status code {resp.status_code}."
                    )

                data = resp.json()
                current = data.get("current", {})
                daily = data.get("daily", {})

                wmo_code = current.get("weather_code", 0)
                condition_desc = WMO_CODE_MAP.get(wmo_code, "Partly cloudy")

                # Generate concise agricultural forecast summary
                forecast_summary = self._summarize_forecast(daily)

                return WeatherContext(
                    location=resolved_name,
                    latitude=lat,
                    longitude=lon,
                    temperature=current.get("temperature_2m"),
                    humidity=current.get("relative_humidity_2m"),
                    precipitation=current.get("precipitation"),
                    wind_speed=current.get("wind_speed_10m"),
                    condition=condition_desc,
                    forecast_summary=forecast_summary,
                    is_available=True,
                    note="Live Open-Meteo weather retrieved."
                )

        except httpx.TimeoutException:
            return WeatherContext(
                location=resolved_name,
                latitude=lat,
                longitude=lon,
                is_available=False,
                note="Weather API request timed out. Proceeding with static agricultural evidence."
            )
        except Exception as e:
            return WeatherContext(
                location=resolved_name,
                latitude=lat,
                longitude=lon,
                is_available=False,
                note=f"Weather fetch error: {str(e)}. Proceeding without weather context."
            )

    def _summarize_forecast(self, daily: Dict[str, Any]) -> str:
        """Create a human-readable 3-day agricultural weather forecast summary."""
        dates = daily.get("time", [])
        precips = daily.get("precipitation_sum", [])
        temp_maxs = daily.get("temperature_2m_max", [])
        temp_mins = daily.get("temperature_2m_min", [])

        if not dates or not precips:
            return "3-day forecast data unavailable."

        total_rain = sum([p for p in precips if p is not None])
        max_temp = max([t for t in temp_maxs if t is not None]) if temp_maxs else "N/A"
        min_temp = min([t for t in temp_mins if t is not None]) if temp_mins else "N/A"

        rain_outlook = (
            "Dry conditions expected (no significant rain)."
            if total_rain < 2.0
            else f"Rain expected ({round(total_rain, 1)} mm over next 3 days)."
        )

        return f"3-Day Outlook: {rain_outlook} Temp range: {min_temp}°C to {max_temp}°C."


# Global instance
weather_service = WeatherService()

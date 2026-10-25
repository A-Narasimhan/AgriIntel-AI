"""
Application configuration.

Centralizes environment variables and settings across AgriIntel AI.
No other file should directly call os.environ or hardcode configurations.
"""

from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # General application metadata
    app_name: str = "AgriIntel AI"
    app_env: str = "development"
    app_version: str = "0.2.0"
    debug: bool = True

    # Storage paths
    data_dir: Path = BASE_DIR / "data"
    knowledge_base_dir: Path = BASE_DIR / "data" / "knowledge_base"
    chroma_db_dir: Path = BASE_DIR / "data" / "chroma"
    sqlite_db_path: Path = BASE_DIR / "data" / "interactions.db"
    sources_registry_path: Path = BASE_DIR / "data" / "knowledge_base" / "sources.json"
    evaluation_dir: Path = BASE_DIR / "data" / "evaluation"

    # Embedding and Vector Store
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_collection_name: str = "agri_knowledge"
    chunk_size: int = 1000
    chunk_overlap: int = 100
    default_top_k: int = 4

    # Supported Crops
    supported_crops: List[str] = ["rice", "cotton", "maize", "groundnut", "soybean"]

    # Weather API (Open-Meteo)
    weather_timeout_seconds: float = 10.0
    weather_geocoding_url: str = "https://geocoding-api.open-meteo.com/v1/search"
    weather_forecast_url: str = "https://api.open-meteo.com/v1/forecast"

    # LLM Settings
    # Supported: mock, gemini, openai, groq, ollama
    llm_provider: str = "mock"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

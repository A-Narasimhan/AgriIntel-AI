"""
FastAPI application entrypoint for AgriIntel AI.

Configures CORS, registers API routers, and exposes OpenAPI documentation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AgriIntel AI: Smart Agricultural Advisory and Dataset Generation "
        "from Farmer Queries and Weather Intelligence."
    ),
)

# Enable CORS for frontend clients (React/Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

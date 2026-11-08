"""Liveness and configuration discovery. Secrets are never returned."""

from fastapi import APIRouter, Depends

from app.api.deps import get_providers_dep, get_settings_dep
from app.config.settings import Settings
from app.providers.registry import ProviderBundle
from app.services.health import build_health_payload

router = APIRouter(tags=["health"])


@router.get("/")
def root(settings: Settings = Depends(get_settings_dep)) -> dict:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health(
    settings: Settings = Depends(get_settings_dep),
    providers: ProviderBundle = Depends(get_providers_dep),
) -> dict:
    return build_health_payload(settings, providers)

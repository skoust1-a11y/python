"""Health/readiness information used by the API."""

from app.config.settings import Settings
from app.providers.registry import ProviderBundle


def build_health_payload(settings: Settings, providers: ProviderBundle) -> dict:
    """Describe process status without exposing secrets."""
    return {
        "status": "ok",
        "name": settings.app_name,
        "environment": settings.app_env,
        "providers": {
            "llm": providers.llm.name,
            "market_data": providers.market_data.name,
            "fundamental_data": providers.fundamentals.name,
            "news": providers.news.name,
        },
    }

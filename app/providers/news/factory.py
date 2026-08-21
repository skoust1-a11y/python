"""Select a news adapter from `NEWS_PROVIDER`.

Adding a vendor means a new module under this package and a registry entry
here. Callers keep depending on `NewsDataProvider`.
"""

from __future__ import annotations

import logging

from app.config.settings import Settings
from app.providers.contracts import NewsDataProvider
from app.providers.news.stub import StubNewsDataProvider
from app.providers.selection import normalize_provider_name, resolve_provider

logger = logging.getLogger("app.providers.news")

NEWS_ADAPTERS: dict[str, type[NewsDataProvider]] = {
    "stub": StubNewsDataProvider,
}


def normalize_news_provider(value: str) -> str:
    return normalize_provider_name(value)


def available_news_providers() -> str:
    return ", ".join(sorted(NEWS_ADAPTERS))


def build_news_data_provider(settings: Settings) -> NewsDataProvider:
    """Instantiate the news adapter named by `NEWS_PROVIDER`."""
    provider = resolve_provider(
        "NEWS_PROVIDER",
        settings.news_provider,
        NEWS_ADAPTERS,
        settings,
    )
    logger.info("Instantiated news provider '%s'", provider.name)
    return provider

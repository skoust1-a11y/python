"""Placeholder news adapter. Does not invent headlines."""

from __future__ import annotations

from datetime import datetime

from app.config.settings import Settings
from app.exceptions import ProviderNotImplementedError
from app.models.news import NewsArticle
from app.providers.contracts import NewsDataProvider


class StubNewsDataProvider(NewsDataProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "stub"

    def get_company_news(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        raise self._unavailable("Company news")

    def get_market_news(
        self,
        *,
        query: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        raise self._unavailable("Market news")

    def _unavailable(self, artifact: str) -> ProviderNotImplementedError:
        return ProviderNotImplementedError(
            "News adapter is not implemented yet. "
            f"{artifact} must come from an external provider, not from application stubs or LLM knowledge."
        )


StubNewsProvider = StubNewsDataProvider

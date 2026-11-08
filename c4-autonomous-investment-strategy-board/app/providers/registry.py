"""Compose configured adapters into a single injectable bundle.

LLM adapters are registered in `app.providers.llm.factory`. Market, fundamental,
and news adapters are registered in their domain factories. Agent and service
code stays unchanged when a vendor is added.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config.settings import Settings
from app.providers.contracts import (
    FundamentalDataProvider,
    LLMProvider,
    MarketDataProvider,
    NewsDataProvider,
)
from app.providers.fundamentals.factory import (
    FUNDAMENTAL_DATA_ADAPTERS,
    build_fundamental_data_provider,
)
from app.providers.llm.factory import build_llm_provider
from app.providers.market_data.factory import (
    MARKET_DATA_ADAPTERS,
    build_market_data_provider,
)
from app.providers.news.factory import NEWS_ADAPTERS, build_news_data_provider

NewsProvider = NewsDataProvider


@dataclass(frozen=True)
class ProviderBundle:
    """Resolved adapters for a single process. Inject this into services."""

    llm: LLMProvider
    market_data: MarketDataProvider
    fundamentals: FundamentalDataProvider
    news: NewsDataProvider


def build_providers(settings: Settings) -> ProviderBundle:
    """Construct adapters from configuration. No vendor is assumed by callers."""
    return ProviderBundle(
        llm=build_llm_provider(settings),
        market_data=build_market_data_provider(settings),
        fundamentals=build_fundamental_data_provider(settings),
        news=build_news_data_provider(settings),
    )


__all__ = [
    "FUNDAMENTAL_DATA_ADAPTERS",
    "MARKET_DATA_ADAPTERS",
    "NEWS_ADAPTERS",
    "NewsProvider",
    "ProviderBundle",
    "build_providers",
]

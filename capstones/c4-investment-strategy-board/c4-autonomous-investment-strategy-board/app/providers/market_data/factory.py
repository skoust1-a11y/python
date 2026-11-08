"""Select a market-data adapter from `MARKET_DATA_PROVIDER`.

Adding a vendor means a new module under this package and a registry entry
here. Callers keep depending on `MarketDataProvider`.
"""

from __future__ import annotations

import logging

from app.config.settings import Settings
from app.providers.contracts import MarketDataProvider
from app.providers.market_data.stub import StubMarketDataProvider
from app.providers.market_data.yahoo import YahooMarketDataProvider
from app.providers.selection import normalize_provider_name, resolve_provider

logger = logging.getLogger("app.providers.market_data")

MARKET_DATA_ADAPTERS: dict[str, type[MarketDataProvider]] = {
    "stub": StubMarketDataProvider,
    "yahoo": YahooMarketDataProvider,
    "yfinance": YahooMarketDataProvider,
}


def normalize_market_data_provider(value: str) -> str:
    return normalize_provider_name(value)


def available_market_data_providers() -> str:
    return ", ".join(sorted(MARKET_DATA_ADAPTERS))


def build_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Instantiate the market-data adapter named by `MARKET_DATA_PROVIDER`."""
    provider = resolve_provider(
        "MARKET_DATA_PROVIDER",
        settings.market_data_provider,
        MARKET_DATA_ADAPTERS,
        settings,
    )
    logger.info("Instantiated market-data provider '%s'", provider.name)
    return provider

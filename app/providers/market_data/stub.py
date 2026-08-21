"""Placeholder market-data adapter. Does not invent or fetch prices."""

from __future__ import annotations

from datetime import datetime

from app.config.settings import Settings
from app.exceptions import ProviderNotImplementedError
from app.models.market import (
    InstrumentMatch,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.providers.contracts import MarketDataProvider


class StubMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    @property
    def name(self) -> str:
        return "stub"

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        raise self._unavailable("Instrument search")

    def get_quote(self, instrument: str) -> MarketQuote:
        raise self._unavailable("Quotes")

    def get_historical_ohlc(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
    ) -> OhlcSeries:
        raise self._unavailable("Historical OHLC data")

    def get_index(self, symbol: str) -> MarketIndex:
        raise self._unavailable("Index information")

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        raise self._unavailable("Volume")

    def get_market_info(self, instrument: str) -> MarketInfo:
        raise self._unavailable("Market information")

    def _unavailable(self, artifact: str) -> ProviderNotImplementedError:
        return ProviderNotImplementedError(
            "Market-data adapter is not implemented yet. "
            f"{artifact} must come from an external provider, not from application stubs or LLM knowledge."
        )

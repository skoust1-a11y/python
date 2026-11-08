"""Market-data provider adapters.

Services depend on `MarketDataProvider`. Concrete vendors are selected by
`MARKET_DATA_PROVIDER` through `build_market_data_provider`.
"""

from app.providers.market_data.factory import (
    MARKET_DATA_ADAPTERS,
    build_market_data_provider,
    normalize_market_data_provider,
)

__all__ = [
    "MARKET_DATA_ADAPTERS",
    "build_market_data_provider",
    "normalize_market_data_provider",
]

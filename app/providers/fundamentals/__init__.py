"""Fundamental-data provider adapters.

Services depend on `FundamentalDataProvider`. Concrete vendors are selected by
`FUNDAMENTAL_DATA_PROVIDER` through `build_fundamental_data_provider`.
"""

from app.providers.fundamentals.factory import (
    FUNDAMENTAL_DATA_ADAPTERS,
    build_fundamental_data_provider,
    normalize_fundamental_data_provider,
)

__all__ = [
    "FUNDAMENTAL_DATA_ADAPTERS",
    "build_fundamental_data_provider",
    "normalize_fundamental_data_provider",
]

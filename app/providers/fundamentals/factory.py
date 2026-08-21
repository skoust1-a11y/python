"""Select a fundamentals adapter from `FUNDAMENTAL_DATA_PROVIDER`.

Adding a vendor means a new module under this package and a registry entry
here. Callers keep depending on `FundamentalDataProvider`.
"""

from __future__ import annotations

import logging

from app.config.settings import Settings
from app.providers.contracts import FundamentalDataProvider
from app.providers.fundamentals.stub import StubFundamentalDataProvider
from app.providers.selection import normalize_provider_name, resolve_provider

logger = logging.getLogger("app.providers.fundamentals")

FUNDAMENTAL_DATA_ADAPTERS: dict[str, type[FundamentalDataProvider]] = {
    "stub": StubFundamentalDataProvider,
}


def normalize_fundamental_data_provider(value: str) -> str:
    return normalize_provider_name(value)


def available_fundamental_data_providers() -> str:
    return ", ".join(sorted(FUNDAMENTAL_DATA_ADAPTERS))


def build_fundamental_data_provider(settings: Settings) -> FundamentalDataProvider:
    """Instantiate the fundamentals adapter named by `FUNDAMENTAL_DATA_PROVIDER`."""
    provider = resolve_provider(
        "FUNDAMENTAL_DATA_PROVIDER",
        settings.fundamental_data_provider,
        FUNDAMENTAL_DATA_ADAPTERS,
        settings,
    )
    logger.info("Instantiated fundamental-data provider '%s'", provider.name)
    return provider

"""Shared adapter lookup used by domain-specific factories.

Vendor SDKs and API shapes stay inside adapter modules. Factories only map a
configured name onto a registered class.
"""

from __future__ import annotations

from typing import TypeVar

from app.config.settings import Settings
from app.exceptions import ConfigurationError

TAdapter = TypeVar("TAdapter")


def normalize_provider_name(value: str) -> str:
    """Normalize a configured provider name to a registry key."""
    return value.strip().lower().replace("-", "_")


def available_adapters(adapters: dict[str, type]) -> str:
    return ", ".join(sorted(adapters)) or "(none)"


def resolve_provider(
    kind: str,
    configured: str,
    adapters: dict[str, type[TAdapter]],
    settings: Settings,
) -> TAdapter:
    """Instantiate the adapter registered for `configured`.

    `kind` is the environment variable name used in error messages
    (for example, `MARKET_DATA_PROVIDER`).
    """
    if not configured.strip():
        raise ConfigurationError(f"{kind} is required.")
    key = normalize_provider_name(configured)
    adapter_cls = adapters.get(key)
    if adapter_cls is None:
        raise ConfigurationError(
            f"Unknown {kind} '{configured}'. Available adapters: {available_adapters(adapters)}."
        )
    return adapter_cls(settings)

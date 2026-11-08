"""LLM error wrapping with secret redaction.

Vendor exceptions and log lines must never include API keys.
"""

from __future__ import annotations

import re

from app.exceptions import ProviderError

_SECRET_PATTERNS = (
    re.compile(r"sk-proj-[A-Za-z0-9_\-]+"),
    re.compile(r"sk-[A-Za-z0-9_\-]+"),
    re.compile(r"gsk_[A-Za-z0-9_\-]+"),
    re.compile(r"AIza[A-Za-z0-9_\-]+"),
    re.compile(r"(?i)(api[_-]?key|authorization|bearer)\s*[:=]\s*\S+"),
)


def redact_secrets(text: str, extra_secrets: list[str] | tuple[str, ...] = ()) -> str:
    """Replace known secret values and common key patterns."""
    redacted = text
    for secret in extra_secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def is_timeout_error(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    if isinstance(exc, TimeoutError) or "timeout" in name:
        return True
    message = str(exc).lower()
    return "timed out" in message or "timeout" in message


def to_provider_error(exc: BaseException, extra_secrets: list[str] | tuple[str, ...] = ()) -> ProviderError:
    """Convert a vendor/SDK failure into a safe ProviderError."""
    raw = str(exc) or type(exc).__name__
    message = redact_secrets(raw, extra_secrets)
    if is_timeout_error(exc):
        return ProviderError(f"LLM request timed out: {message}")
    return ProviderError(f"LLM provider request failed: {message}")

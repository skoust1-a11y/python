"""Shared types for configurable AI response modes."""

from typing import Literal

ResponseMode = Literal["strict", "explain", "analysis"]

RESPONSE_MODES: tuple[ResponseMode, ...] = (
    "strict",
    "explain",
    "analysis",
)
DEFAULT_RESPONSE_MODE: ResponseMode = "explain"

"""Retry policy for MCP network operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.mcp.exceptions import MCPConnectionError, MCPSearchError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class MCPRetryPolicy:
    """Configurable retry settings for MCP calls."""

    max_attempts: int = 3
    min_wait_seconds: float = 1.0
    max_wait_seconds: float = 10.0

    def _log_retry(self, retry_state: RetryCallState) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        logger.warning(
            "MCP call retry %s/%s after error: %s",
            retry_state.attempt_number,
            self.max_attempts,
            exc,
        )

    def wrap(self, func: Callable[..., T]) -> Callable[..., T]:
        """Return func decorated with exponential-backoff retries."""
        if self.max_attempts <= 1:
            return func

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(
                multiplier=self.min_wait_seconds,
                max=self.max_wait_seconds,
            ),
            retry=retry_if_exception_type((MCPConnectionError, MCPSearchError)),
            before_sleep=self._log_retry,
        )
        async def _wrapped(*args, **kwargs):
            return await func(*args, **kwargs)

        return _wrapped  # type: ignore[return-value]

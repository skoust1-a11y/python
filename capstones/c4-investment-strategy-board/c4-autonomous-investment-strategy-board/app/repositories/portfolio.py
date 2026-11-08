"""In-memory persistence for staged uploads and confirmed portfolios.

The prototype has no database. This store is the persistence boundary so
services never hardcode a storage engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Protocol

from app.models.analysis import PortfolioAnalysisResult
from app.models.portfolio import Holding, Portfolio, PortfolioPreview


@dataclass
class PortfolioDraft:
    """A validated upload waiting for explicit confirmation."""

    id: str
    filename: str
    created_at: datetime
    expires_at: datetime
    preview: PortfolioPreview
    importable: list[Holding] = field(default_factory=list)
    imported_portfolio_id: str | None = None


class PortfolioStore(Protocol):
    """Persistence contract for drafts and imported portfolios."""

    def save_draft(self, draft: PortfolioDraft) -> None:
        """Insert or replace a staged upload."""

    def get_draft(self, upload_id: str) -> PortfolioDraft | None:
        """Return a non-expired draft, or None."""

    def mark_draft_imported(self, upload_id: str, portfolio_id: str) -> None:
        """Record that a draft was confirmed."""

    def save_portfolio(self, portfolio: Portfolio) -> None:
        """Persist a confirmed portfolio."""

    def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        """Return an imported portfolio, or None."""

    def list_portfolios(self) -> list[Portfolio]:
        """Return imported portfolios, newest first."""

    def save_analysis(self, result: PortfolioAnalysisResult) -> None:
        """Persist a completed analysis run."""

    def get_analysis(self, analysis_id: str) -> PortfolioAnalysisResult | None:
        """Return a stored analysis, or None."""

    def list_analyses(self, portfolio_id: str) -> list[PortfolioAnalysisResult]:
        """Return analyses for one portfolio, newest first."""


class InMemoryPortfolioStore:
    """Process-local store used by the prototype API."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._drafts: dict[str, PortfolioDraft] = {}
        self._portfolios: dict[str, Portfolio] = {}
        self._analyses: dict[str, PortfolioAnalysisResult] = {}

    def save_draft(self, draft: PortfolioDraft) -> None:
        with self._lock:
            self._purge_expired_unlocked(datetime.now(timezone.utc))
            self._drafts[draft.id] = draft

    def get_draft(self, upload_id: str) -> PortfolioDraft | None:
        with self._lock:
            self._purge_expired_unlocked(datetime.now(timezone.utc))
            return self._drafts.get(upload_id)

    def mark_draft_imported(self, upload_id: str, portfolio_id: str) -> None:
        with self._lock:
            draft = self._drafts.get(upload_id)
            if draft is None:
                return
            preview = draft.preview.model_copy(update={"imported_portfolio_id": portfolio_id})
            self._drafts[upload_id] = PortfolioDraft(
                id=draft.id,
                filename=draft.filename,
                created_at=draft.created_at,
                expires_at=draft.expires_at,
                preview=preview,
                importable=list(draft.importable),
                imported_portfolio_id=portfolio_id,
            )

    def save_portfolio(self, portfolio: Portfolio) -> None:
        with self._lock:
            self._portfolios[portfolio.id] = portfolio

    def get_portfolio(self, portfolio_id: str) -> Portfolio | None:
        with self._lock:
            return self._portfolios.get(portfolio_id)

    def list_portfolios(self) -> list[Portfolio]:
        with self._lock:
            portfolios = list(self._portfolios.values())
        return sorted(portfolios, key=lambda item: item.imported_at, reverse=True)

    def save_analysis(self, result: PortfolioAnalysisResult) -> None:
        with self._lock:
            self._analyses[result.id] = result

    def get_analysis(self, analysis_id: str) -> PortfolioAnalysisResult | None:
        with self._lock:
            return self._analyses.get(analysis_id)

    def list_analyses(self, portfolio_id: str) -> list[PortfolioAnalysisResult]:
        with self._lock:
            matches = [
                item for item in self._analyses.values() if item.portfolio_id == portfolio_id
            ]
        return sorted(matches, key=lambda item: item.created_at, reverse=True)

    def _purge_expired_unlocked(self, now: datetime) -> None:
        expired = [
            upload_id
            for upload_id, draft in self._drafts.items()
            if draft.imported_portfolio_id is None and draft.expires_at <= now
        ]
        for upload_id in expired:
            self._drafts.pop(upload_id, None)


def draft_expiry(created_at: datetime, ttl_seconds: int) -> datetime:
    return created_at + timedelta(seconds=ttl_seconds)

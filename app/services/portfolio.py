"""Portfolio upload, preview, confirmation, and retrieval.

Market, fundamental, and news providers are not used. Confirmation is required
before a staged upload becomes an available portfolio.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.config.settings import Settings
from app.exceptions import NotFoundError, PortfolioImportError
from app.models.portfolio import (
    Portfolio,
    PortfolioHoldings,
    PortfolioPreview,
    PortfolioSummary,
)
from app.repositories.portfolio import PortfolioDraft, PortfolioStore, draft_expiry
from app.tools.portfolio import parse_portfolio_file, validate_upload_file


def stage_portfolio_upload(
    store: PortfolioStore,
    settings: Settings,
    *,
    filename: str | None,
    content: bytes,
) -> PortfolioPreview:
    """Validate a file, parse holdings, and stage a preview pending confirmation."""
    original_name, fmt = validate_upload_file(
        filename=filename,
        content=content,
        max_bytes=settings.portfolio_max_upload_bytes,
    )
    parsed = parse_portfolio_file(filename=original_name, content=content, fmt=fmt)
    created_at = datetime.now(timezone.utc)
    upload_id = uuid4().hex
    expires_at = draft_expiry(created_at, settings.portfolio_upload_ttl_seconds)
    if parsed.errors:
        status = "invalid"
    elif parsed.warnings:
        status = "valid_with_warnings"
    else:
        status = "valid"
    preview = PortfolioPreview(
        upload_id=upload_id,
        status=status,
        can_confirm=parsed.can_confirm,
        filename=original_name,
        format=parsed.format,
        holdings=parsed.holdings,
        issues=parsed.issues,
        created_at=created_at,
        expires_at=expires_at,
    )
    store.save_draft(
        PortfolioDraft(
            id=upload_id,
            filename=original_name,
            created_at=created_at,
            expires_at=expires_at,
            preview=preview,
            importable=list(parsed.importable),
        )
    )
    return preview


def get_portfolio_preview(store: PortfolioStore, upload_id: str) -> PortfolioPreview:
    draft = _require_draft(store, upload_id)
    return draft.preview


def confirm_portfolio_upload(
    store: PortfolioStore,
    upload_id: str,
    *,
    name: str | None = None,
) -> Portfolio:
    """Import a staged preview. Rejected when validation errors remain."""
    draft = _require_draft(store, upload_id)
    if draft.imported_portfolio_id:
        raise PortfolioImportError(
            "This upload has already been imported.",
            issues=[
                {
                    "severity": "error",
                    "code": "already_imported",
                    "message": "This upload has already been imported.",
                    "value": draft.imported_portfolio_id,
                }
            ],
        )
    if not draft.preview.can_confirm or not draft.importable:
        raise PortfolioImportError(
            "This portfolio cannot be imported until validation errors are resolved.",
            issues=[item.model_dump() for item in draft.preview.issues if item.severity == "error"],
        )
    imported_at = datetime.now(timezone.utc)
    portfolio_id = uuid4().hex
    label = name.strip() if name and name.strip() else None
    currencies = {holding.currency for holding in draft.importable if holding.currency}
    base_currency = next(iter(currencies)) if len(currencies) == 1 else None
    portfolio = Portfolio(
        id=portfolio_id,
        status="imported",
        name=label,
        holdings=list(draft.importable),
        base_currency=base_currency,
        source_filename=draft.filename,
        source_format=draft.preview.format or "csv",
        imported_at=imported_at,
        upload_id=draft.id,
    )
    store.save_portfolio(portfolio)
    store.mark_draft_imported(draft.id, portfolio.id)
    return portfolio


def get_imported_portfolio(store: PortfolioStore, portfolio_id: str) -> Portfolio:
    portfolio = store.get_portfolio(portfolio_id)
    if portfolio is None:
        raise NotFoundError("Portfolio not found.")
    return portfolio


def get_imported_portfolio_summary(store: PortfolioStore, portfolio_id: str) -> PortfolioSummary:
    return _to_summary(get_imported_portfolio(store, portfolio_id))


def get_imported_holdings(store: PortfolioStore, portfolio_id: str) -> PortfolioHoldings:
    portfolio = get_imported_portfolio(store, portfolio_id)
    return PortfolioHoldings(portfolio_id=portfolio.id, holdings=list(portfolio.holdings))


def list_imported_portfolios(store: PortfolioStore) -> list[PortfolioSummary]:
    return [_to_summary(item) for item in store.list_portfolios()]


def _to_summary(item: Portfolio) -> PortfolioSummary:
    return PortfolioSummary(
        id=item.id,
        status=item.status,
        name=item.name,
        holding_count=item.holding_count,
        base_currency=item.base_currency,
        source_filename=item.source_filename,
        source_format=item.source_format,
        imported_at=item.imported_at,
    )


def _require_draft(store: PortfolioStore, upload_id: str) -> PortfolioDraft:
    draft = store.get_draft(upload_id)
    if draft is None:
        raise NotFoundError("Portfolio upload not found.")
    return draft

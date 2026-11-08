"""Parse a holdings CSV and persist a user-uploaded book."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Holding, Portfolio

MAX_BYTES = 1_000_000
MAX_ROWS = 200
RISK_CATEGORIES = ("Low", "Medium", "High")

_ALIASES = {
    "asset_name": {"asset_name", "asset", "name", "ticker", "symbol"},
    "asset_type": {"asset_type", "type"},
    "sector": {"sector"},
    "allocation_percentage": {"allocation_percentage", "allocation", "weight", "weight_pct"},
    "market_value": {"market_value", "value", "mv", "amount"},
    "buy_price": {"buy_price", "buying_price", "purchase_price", "cost", "cost_price"},
    "buy_date": {"buy_date", "buying_date", "purchase_date", "bought_on", "date"},
    "last_updated": {"last_updated", "as_of"},
}


class PortfolioImportError(ValueError):
    pass


def _norm_header(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _header_map(fieldnames: Optional[List[str]]) -> Dict[str, str]:
    if not fieldnames:
        raise PortfolioImportError("CSV must include a header row")
    mapping: Dict[str, str] = {}
    for raw in fieldnames:
        key = _norm_header(raw)
        for dest, aliases in _ALIASES.items():
            if key in aliases:
                mapping[dest] = raw
                break
    if "asset_name" not in mapping:
        raise PortfolioImportError("CSV needs an asset_name (or name/ticker) column")
    return mapping


def _decimal(raw: str, field: str, default: Optional[Decimal] = None) -> Optional[Decimal]:
    text = (raw or "").strip().replace(",", "")
    if text == "":
        return default
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise PortfolioImportError("invalid {} value {!r}".format(field, raw)) from exc


def _parse_date(raw: str, field: str, default: Optional[date] = None) -> Optional[date]:
    text = (raw or "").strip()
    if not text:
        return default
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise PortfolioImportError("invalid {} {!r}; use YYYY-MM-DD".format(field, raw))


def parse_holdings_csv(text: str) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        raise PortfolioImportError("CSV is empty")
    reader = csv.DictReader(io.StringIO(text))
    mapping = _header_map(reader.fieldnames)
    rows: List[Dict[str, Any]] = []
    for index, raw in enumerate(reader, start=2):
        name = (raw.get(mapping["asset_name"]) or "").strip()
        if not name and not any((v or "").strip() for v in raw.values()):
            continue
        if not name:
            raise PortfolioImportError("row {} is missing asset_name".format(index))
        alloc = _decimal(raw.get(mapping.get("allocation_percentage", ""), ""), "allocation_percentage", Decimal("0"))
        value = _decimal(raw.get(mapping.get("market_value", ""), ""), "market_value", Decimal("0"))
        rows.append(
            {
                "asset_name": name[:150],
                "asset_type": (raw.get(mapping.get("asset_type", ""), "") or "").strip()[:100] or "Equity",
                "sector": (raw.get(mapping.get("sector", ""), "") or "").strip()[:100] or "Unknown",
                "allocation_percentage": float(alloc or 0),
                "market_value": value or Decimal("0"),
                "buy_price": _decimal(raw.get(mapping.get("buy_price", ""), ""), "buy_price"),
                "buy_date": _parse_date(raw.get(mapping.get("buy_date", ""), ""), "buy_date"),
                "last_updated": _parse_date(raw.get(mapping.get("last_updated", ""), ""), "last_updated", date.today()),
            }
        )
        if len(rows) > MAX_ROWS:
            raise PortfolioImportError("CSV has more than {} holdings".format(MAX_ROWS))
    if not rows:
        raise PortfolioImportError("CSV has no holdings")
    return rows


def normalize_risk(raw: str) -> str:
    value = (raw or "").strip().title() or "Medium"
    if value not in RISK_CATEGORIES:
        raise PortfolioImportError("risk_category must be Low, Medium, or High")
    return value


def persist_uploaded_book(
    session: Session,
    *,
    name: str,
    manager: str,
    risk: str,
    benchmark: str,
    rows: List[Dict[str, Any]],
) -> Portfolio:
    title = (name or "").strip()
    if not title:
        raise PortfolioImportError("portfolio_name is required")
    next_pid = (session.query(func.max(Portfolio.portfolio_id)).scalar() or 0) + 1
    next_hid = (session.query(func.max(Holding.holding_id)).scalar() or 0) + 1
    book = Portfolio(
        portfolio_id=next_pid,
        portfolio_name=title[:150],
        portfolio_manager=(manager or "").strip()[:150] or None,
        risk_category=normalize_risk(risk),
        total_value=sum((row["market_value"] for row in rows), Decimal("0")),
        benchmark_index=(benchmark or "").strip()[:100] or None,
    )
    session.add(book)
    session.flush()
    for offset, row in enumerate(rows):
        session.add(
            Holding(
                holding_id=next_hid + offset,
                portfolio_id=book.portfolio_id,
                asset_name=row["asset_name"],
                asset_type=row["asset_type"],
                sector=row["sector"],
                allocation_percentage=row["allocation_percentage"],
                market_value=row["market_value"],
                buy_price=row["buy_price"],
                buy_date=row["buy_date"],
                last_updated=row["last_updated"],
            )
        )
    session.flush()
    return book

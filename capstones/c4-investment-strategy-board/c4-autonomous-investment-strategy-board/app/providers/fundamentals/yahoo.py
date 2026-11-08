"""Yahoo Finance fundamental-data adapter.

Vendor SDK usage stays in this module. Callers depend on `FundamentalDataProvider`.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, timezone
from typing import Any

from app.config.settings import Settings
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.fundamentals import (
    CompanyProfile,
    FinancialMetrics,
    FinancialStatement,
    ReportingPeriod,
    StatementType,
    ValuationMetrics,
)
from app.models.types import normalize_symbol
from app.providers.contracts import FundamentalDataProvider
from app.tools.fundamentals import normalize_line_item_key

logger = logging.getLogger("app.providers.fundamentals")
UTC = timezone.utc
_SOURCE_NAME = "yahoo-finance"


class YahooFundamentalDataProvider(FundamentalDataProvider):
    """Company profiles, financial statements, key metrics, and valuation via Yahoo Finance."""

    def __init__(self, settings: Settings | None = None, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def name(self) -> str:
        return "yahoo"

    def get_company_profile(self, instrument: str) -> CompanyProfile:
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            info = _mapping(getattr(ticker, "info", None))
            fast = _mapping(getattr(ticker, "fast_info", None))
        except Exception as exc:
            raise self._failed(f"Company profile for {requested}", exc) from exc

        name = _optional_text(info.get("longName") or info.get("shortName"))
        sector = _optional_text(info.get("sector"))
        industry = _optional_text(info.get("industry"))
        description = _optional_text(info.get("longBusinessSummary") or info.get("description"))
        country = _optional_text(info.get("country"))
        currency = _currency_code(info.get("currency") or fast.get("currency") or info.get("financialCurrency"))
        exchange = _exchange_code(fast.get("exchange") or info.get("exchange") or info.get("fullExchangeName"))
        website = _http_url(info.get("website"))
        employees = _non_negative_int(info.get("fullTimeEmployees"))
        timestamp = datetime.now(tz=UTC)

        return CompanyProfile(
            symbol=requested,
            name=name,
            sector=sector,
            industry=industry,
            description=description,
            country=country,
            currency=currency,
            exchange=exchange,
            website=website,
            employees=employees,
            timestamp=timestamp,
            source=self._source(vendor_symbol, timestamp),
            extra=_public_extra(
                {
                    "vendor_symbol": vendor_symbol,
                    "city": _optional_text(info.get("city")),
                    "state": _optional_text(info.get("state")),
                    "address": _optional_text(info.get("address1")),
                }
            ),
        )

    def get_financial_statements(
        self,
        instrument: str,
        *,
        statement_type: StatementType = "income",
        period: ReportingPeriod = "annual",
    ) -> list[FinancialStatement]:
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            if statement_type == "income":
                frame = ticker.income_stmt if period == "annual" else ticker.quarterly_income_stmt
            elif statement_type == "balance_sheet":
                frame = ticker.balance_sheet if period == "annual" else ticker.quarterly_balance_sheet
            elif statement_type == "cash_flow":
                frame = ticker.cashflow if period == "annual" else ticker.quarterly_cashflow
            else:
                raise ProviderError(f"Unsupported statement type '{statement_type}'.")
        except ProviderError:
            raise
        except Exception as exc:
            raise self._failed(f"Financial statements for {requested}", exc) from exc

        if frame is None or getattr(frame, "empty", True):
            return []

        try:
            fast = _mapping(getattr(ticker, "fast_info", None))
            info = _mapping(getattr(ticker, "info", None))
        except Exception:
            fast, info = {}, {}

        currency = _currency_code(info.get("financialCurrency") or info.get("currency") or fast.get("currency"))
        exchange = _exchange_code(fast.get("exchange") or info.get("exchange") or info.get("fullExchangeName"))
        timestamp = datetime.now(tz=UTC)

        statements: list[FinancialStatement] = []
        for column in frame.columns:
            period_end = _extract_date(column)
            line_items: dict[str, Any] = {}
            for item_name, val in frame[column].items():
                num = _finite(val)
                if num is not None:
                    line_items[normalize_line_item_key(str(item_name))] = num

            fiscal_period_str = str(period_end.year) if period_end else None

            statements.append(
                FinancialStatement(
                    symbol=requested,
                    statement_type=statement_type,
                    period=period,
                    source=self._source(vendor_symbol, timestamp),
                    currency=currency,
                    exchange=exchange,
                    period_end=period_end,
                    fiscal_period=fiscal_period_str,
                    timestamp=timestamp,
                    line_items=line_items,
                    extra=_public_extra({"vendor_symbol": vendor_symbol}),
                )
            )

        # Return sorted by period_end (oldest first)
        statements.sort(key=lambda item: item.period_end or date.min)
        return statements

    def get_key_metrics(self, instrument: str) -> FinancialMetrics:
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            info = _mapping(getattr(ticker, "info", None))
            fast = _mapping(getattr(ticker, "fast_info", None))
        except Exception as exc:
            raise self._failed(f"Key financial metrics for {requested}", exc) from exc

        timestamp = datetime.now(tz=UTC)
        currency = _currency_code(info.get("financialCurrency") or info.get("currency") or fast.get("currency"))
        exchange = _exchange_code(fast.get("exchange") or info.get("exchange") or info.get("fullExchangeName"))

        return FinancialMetrics(
            symbol=requested,
            source=self._source(vendor_symbol, timestamp),
            timestamp=timestamp,
            currency=currency,
            exchange=exchange,
            revenue=_first_finite(info.get("totalRevenue"), info.get("revenue")),
            net_income=_first_finite(info.get("netIncomeToCommon"), info.get("netIncome")),
            eps=_first_finite(info.get("trailingEps"), info.get("forwardEps")),
            ebitda=_first_finite(info.get("ebitda")),
            operating_margin=_first_finite(info.get("operatingMargins")),
            profit_margin=_first_finite(info.get("profitMargins")),
            roe=_first_finite(info.get("returnOnEquity")),
            roa=_first_finite(info.get("returnOnAssets")),
            debt_to_equity=_first_finite(info.get("debtToEquity")),
            current_ratio=_first_finite(info.get("currentRatio")),
            pe_ratio=_first_finite(info.get("trailingPE"), info.get("forwardPE")),
            forward_pe=_first_finite(info.get("forwardPE")),
            pb_ratio=_first_finite(info.get("priceToBook")),
            ps_ratio=_first_finite(info.get("priceToSalesTrailing12Months")),
            peg_ratio=_first_finite(info.get("pegRatio")),
            ev_to_ebitda=_first_finite(info.get("enterpriseToEbitda")),
            market_cap=_first_finite(fast.get("market_cap"), info.get("marketCap")),
            enterprise_value=_first_finite(info.get("enterpriseValue")),
            dividend_yield=_first_finite(info.get("dividendYield")),
            extra=_public_extra({"vendor_symbol": vendor_symbol}),
        )

    def get_valuation_metrics(self, instrument: str) -> ValuationMetrics:
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            info = _mapping(getattr(ticker, "info", None))
            fast = _mapping(getattr(ticker, "fast_info", None))
        except Exception as exc:
            raise self._failed(f"Valuation metrics for {requested}", exc) from exc

        timestamp = datetime.now(tz=UTC)
        currency = _currency_code(info.get("currency") or fast.get("currency"))
        exchange = _exchange_code(fast.get("exchange") or info.get("exchange") or info.get("fullExchangeName"))

        return ValuationMetrics(
            symbol=requested,
            source=self._source(vendor_symbol, timestamp),
            timestamp=timestamp,
            currency=currency,
            exchange=exchange,
            pe_ratio=_first_finite(info.get("trailingPE")),
            forward_pe=_first_finite(info.get("forwardPE")),
            pb_ratio=_first_finite(info.get("priceToBook")),
            ps_ratio=_first_finite(info.get("priceToSalesTrailing12Months")),
            peg_ratio=_first_finite(info.get("pegRatio")),
            ev_to_ebitda=_first_finite(info.get("enterpriseToEbitda")),
            market_cap=_first_finite(fast.get("market_cap"), info.get("marketCap")),
            enterprise_value=_first_finite(info.get("enterpriseValue")),
            dividend_yield=_first_finite(info.get("dividendYield")),
            extra=_public_extra({"vendor_symbol": vendor_symbol}),
        )

    def _resolve_ticker(self, instrument: str) -> tuple[Any, str]:
        errors: list[str] = []
        country = (self._settings.default_market_country if self._settings else "IN") or "IN"
        for vendor_symbol in _vendor_candidates(instrument, country=country):
            try:
                ticker = self._yf().Ticker(vendor_symbol)
                if _ticker_has_data(ticker):
                    return ticker, vendor_symbol
            except ProviderError:
                raise
            except Exception as exc:
                errors.append(f"{vendor_symbol}: {exc}")
        detail = f" ({'; '.join(errors)})" if errors else ""
        raise ProviderError(f"Instrument {instrument} was not found.{detail}")

    def _yf(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import yfinance as yf
        except ImportError as exc:
            raise ProviderError("Yahoo Finance adapter requires the yfinance package.") from exc
        return yf

    def _source(self, vendor_symbol: str, timestamp: datetime) -> DataSourceMetadata:
        return DataSourceMetadata(
            provider=self.name,
            source=_SOURCE_NAME,
            timestamp=timestamp,
            url=f"https://finance.yahoo.com/quote/{vendor_symbol}",
            raw_reference=vendor_symbol,
        )

    def _failed(self, artifact: str, exc: BaseException) -> ProviderError:
        message = str(exc).strip() or type(exc).__name__
        return ProviderError(f"{artifact} request failed: {message}")


def _vendor_candidates(instrument: str, country: str = "IN") -> list[str]:
    token = instrument.strip().upper()
    candidates: list[str] = []
    if country.upper() == "IN" and "." not in token and not token.startswith("^"):
        candidates.append(f"{token}.NS")
        candidates.append(f"{token}.BO")
        candidates.append(instrument.strip())
    else:
        candidates.append(instrument.strip())
        if "." not in token and not token.startswith("^"):
            candidates.append(f"{token}.NS")
            candidates.append(f"{token}.BO")
    unique: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        key = item.upper()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _ticker_has_data(ticker: Any) -> bool:
    try:
        fast = _mapping(getattr(ticker, "fast_info", None))
        if _first_finite(fast.get("last_price"), fast.get("lastPrice"), fast.get("market_cap")) is not None:
            return True
        info = _mapping(getattr(ticker, "info", None))
        if info.get("shortName") or info.get("longName") or info.get("symbol") or info.get("sector"):
            return True
    except Exception:
        return False
    return False


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except Exception:
        payload: dict[str, Any] = {}
        for key in dir(value):
            if key.startswith("_"):
                continue
            try:
                item = getattr(value, key)
            except Exception:
                continue
            if callable(item):
                continue
            payload[key] = item
        return payload


def _extract_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    to_pydatetime = getattr(value, "to_pydatetime", None)
    if callable(to_pydatetime):
        res = to_pydatetime()
        if isinstance(res, datetime):
            return res.date()
    try:
        text = str(value)[:10]
        return date.fromisoformat(text)
    except Exception:
        return None


def _first_finite(*values: Any) -> float | None:
    for value in values:
        parsed = _finite(value)
        if parsed is not None:
            return parsed
    return None


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _non_negative_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
        return parsed if parsed >= 0 else None
    except (TypeError, ValueError):
        return None


def _http_url(value: Any) -> str | None:
    text = _optional_text(value)
    if text is None:
        return None
    if not text.startswith("http://") and not text.startswith("https://"):
        text = f"https://{text}"
    try:
        from app.models.types import normalize_http_url

        return normalize_http_url(text)
    except ValueError:
        return None


def _currency_code(value: Any) -> str | None:
    token = _optional_text(value)
    if token is None or len(token) != 3 or not token.isalpha():
        return None
    return token.upper()


def _exchange_code(value: Any) -> str | None:
    token = _optional_text(value)
    if token is None:
        return None
    compact = token.upper().replace(" ", "")
    if compact in {"NSI", "NSE"}:
        return "NSE"
    if compact in {"BSE", "BOM"}:
        return "BSE"
    if compact in {"NMS", "NGM", "NASDAQ"}:
        return "NASDAQ"
    if compact in {"NYQ", "NYSE"}:
        return "NYSE"
    try:
        from app.models.types import normalize_exchange

        return normalize_exchange(compact)
    except ValueError:
        return None


def _public_extra(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in {None, ""}}


def _require_symbol(instrument: str) -> str:
    try:
        return normalize_symbol(instrument)
    except ValueError as exc:
        raise ProviderError("Invalid instrument symbol.") from exc

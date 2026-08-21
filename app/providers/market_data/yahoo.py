"""Yahoo Finance market-data adapter.

Vendor SDK usage stays in this module. Callers depend on `MarketDataProvider`.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.config.settings import Settings
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.market import (
    HistoricalPrice,
    InstrumentMatch,
    MarketIndex,
    MarketInfo,
    MarketQuote,
    OhlcSeries,
    VolumeSnapshot,
)
from app.models.types import normalize_period, normalize_symbol
from app.providers.contracts import MarketDataProvider

UTC = timezone.utc

_SOURCE_NAME = "yahoo-finance"
_VENDOR_INDEX_TICKERS: dict[str, str] = {
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",
    "^NSEI": "^NSEI",
    "SENSEX": "^BSESN",
    "^BSESN": "^BSESN",
    "NIFTYBANK": "^NSEBANK",
    "BANKNIFTY": "^NSEBANK",
    "^NSEBANK": "^NSEBANK",
    "NIFTYIT": "^CNXIT",
    "^CNXIT": "^CNXIT",
    "INDIAVIX": "^INDIAVIX",
    "^INDIAVIX": "^INDIAVIX",
}
_INDEX_NAMES: dict[str, str] = {
    "^NSEI": "NIFTY 50",
    "^BSESN": "SENSEX",
    "^NSEBANK": "NIFTY Bank",
    "^CNXIT": "NIFTY IT",
    "^INDIAVIX": "India VIX",
}
_SESSION_BY_MARKET_STATE: dict[str, str] = {
    "REGULAR": "open",
    "PRE": "pre_market",
    "PREPRE": "pre_market",
    "POST": "after_hours",
    "POSTPOST": "after_hours",
    "CLOSED": "closed",
}
_INTERVAL_MAP: dict[str, str] = {
    "1d": "1d",
    "1h": "1h",
    "1wk": "1wk",
    "1w": "1wk",
    "1mo": "1mo",
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "1h",
}


class YahooMarketDataProvider(MarketDataProvider):
    """Live quotes, indices, search, and OHLC via Yahoo Finance."""

    def __init__(self, settings: Settings | None = None, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def name(self) -> str:
        return "yahoo"

    def search_instruments(self, query: str, *, limit: int = 10) -> list[InstrumentMatch]:
        token = query.strip()
        if not token:
            return []
        capped = max(1, min(limit, 25))
        try:
            search = self._yf().Search(token, max_results=capped)
            rows = list(getattr(search, "quotes", None) or [])
        except Exception as exc:
            raise self._failed("Instrument search", exc) from exc
        matches: list[InstrumentMatch] = []
        seen: set[str] = set()
        retrieved_at = datetime.now(tz=UTC)
        for row in rows:
            if not isinstance(row, dict):
                continue
            symbol = _optional_text(row.get("symbol"))
            if symbol is None:
                continue
            try:
                normalized = normalize_symbol(symbol)
            except ValueError:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            exchange = _exchange_code(row.get("exchange") or row.get("exchDisp"))
            quote_type = _optional_text(row.get("quoteType") or row.get("typeDisp"))
            matches.append(
                InstrumentMatch(
                    symbol=normalized,
                    name=_optional_text(row.get("shortname") or row.get("longname") or row.get("name")),
                    exchange=exchange,
                    currency=_currency_code(row.get("currency")),
                    asset_class=_asset_class(quote_type),
                    source=self._source(normalized, retrieved_at),
                    extra=_public_extra(
                        {
                            "quote_type": quote_type,
                            "exchange_display": _optional_text(row.get("exchDisp")),
                        }
                    ),
                )
            )
            if len(matches) >= capped:
                break
        return matches

    def get_quote(self, instrument: str) -> MarketQuote:
        snapshot = self._snapshot(instrument)
        return MarketQuote(
            symbol=snapshot.requested,
            value=snapshot.price,
            timestamp=snapshot.timestamp,
            currency=snapshot.currency,
            exchange=snapshot.exchange,
            bid=snapshot.bid,
            ask=snapshot.ask,
            change=snapshot.change,
            change_percent=snapshot.change_percent,
            volume=snapshot.volume,
            source=self._source(snapshot.vendor_symbol, snapshot.timestamp),
            extra=_public_extra({"vendor_symbol": snapshot.vendor_symbol}),
        )

    def get_historical_ohlc(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
    ) -> OhlcSeries:
        requested = _require_symbol(instrument)
        period = _require_interval(interval)
        vendor_interval = _INTERVAL_MAP.get(period)
        if vendor_interval is None:
            raise ProviderError(f"Unsupported market interval '{interval}'.")
        ticker, vendor_symbol = self._resolve_ticker(requested)
        kwargs: dict[str, Any] = {"interval": vendor_interval, "auto_adjust": False}
        if start is not None or end is not None:
            kwargs["start"] = start
            kwargs["end"] = end
        else:
            kwargs["period"] = "1y" if period in {"1d", "1wk", "1mo"} else "5d"
        try:
            frame = ticker.history(**kwargs)
        except Exception as exc:
            raise self._failed("Historical OHLC data", exc) from exc
        prices = _ohlc_prices(frame, requested, period, self.name)
        if not prices:
            raise ProviderError(f"Historical OHLC data is unavailable for {requested}.")
        retrieved_at = prices[-1].timestamp
        return OhlcSeries(
            symbol=requested,
            period=period,
            source=self._source(vendor_symbol, retrieved_at),
            start=prices[0].timestamp,
            end=prices[-1].timestamp,
            prices=prices,
            extra=_public_extra({"vendor_symbol": vendor_symbol}),
        )

    def get_index(self, symbol: str) -> MarketIndex:
        snapshot = self._snapshot(symbol)
        return MarketIndex(
            symbol=snapshot.requested,
            value=snapshot.price,
            timestamp=snapshot.timestamp,
            name=snapshot.name or _INDEX_NAMES.get(snapshot.vendor_symbol),
            currency=snapshot.currency,
            exchange=snapshot.exchange,
            change=snapshot.change,
            change_percent=snapshot.change_percent,
            source=self._source(snapshot.vendor_symbol, snapshot.timestamp),
            extra=_public_extra({"vendor_symbol": snapshot.vendor_symbol}),
        )

    def get_volume(self, instrument: str) -> VolumeSnapshot:
        snapshot = self._snapshot(instrument)
        if snapshot.volume is None:
            raise ProviderError(f"Volume is unavailable for {snapshot.requested}.")
        return VolumeSnapshot(
            symbol=snapshot.requested,
            value=snapshot.volume,
            timestamp=snapshot.timestamp,
            average_volume=snapshot.average_volume,
            currency=snapshot.currency,
            exchange=snapshot.exchange,
            source=self._source(snapshot.vendor_symbol, snapshot.timestamp),
            extra=_public_extra({"vendor_symbol": snapshot.vendor_symbol}),
        )

    def get_market_info(self, instrument: str) -> MarketInfo:
        snapshot = self._snapshot(instrument)
        return MarketInfo(
            symbol=snapshot.requested,
            name=snapshot.name,
            exchange=snapshot.exchange,
            currency=snapshot.currency,
            asset_class=snapshot.asset_class,
            timezone=snapshot.timezone,
            trading_hours=snapshot.trading_hours,
            session=snapshot.session,
            source=self._source(snapshot.vendor_symbol, snapshot.timestamp),
            extra=_public_extra(
                {
                    "vendor_symbol": snapshot.vendor_symbol,
                    "session": snapshot.session,
                    "market_state": snapshot.market_state,
                }
            ),
        )

    def _snapshot(self, instrument: str) -> "_YahooSnapshot":
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            fast = _mapping(getattr(ticker, "fast_info", None))
            info = _mapping(getattr(ticker, "info", None))
        except Exception as exc:
            raise self._failed(f"Market data for {requested}", exc) from exc
        price = _first_finite(
            fast.get("last_price"),
            fast.get("lastPrice"),
            info.get("regularMarketPrice"),
            info.get("currentPrice"),
        )
        previous = _first_finite(
            fast.get("previous_close"),
            fast.get("previousClose"),
            info.get("regularMarketPreviousClose"),
            info.get("previousClose"),
        )
        if price is None:
            raise ProviderError(f"Quote is unavailable for {requested}.")
        change = _first_finite(info.get("regularMarketChange"), info.get("change"))
        change_percent = _first_finite(
            info.get("regularMarketChangePercent"),
            info.get("changePercent"),
        )
        if change is None and previous is not None:
            change = price - previous
        if change_percent is None and previous not in {None, 0}:
            change_percent = ((price - previous) / previous) * 100.0
        timestamp = _timestamp(
            info.get("regularMarketTime"),
            info.get("postMarketTime"),
            info.get("preMarketTime"),
        )
        if timestamp is None:
            raise ProviderError(f"Quote timestamp is unavailable for {requested}.")
        session = _session(info.get("marketState") or fast.get("market_state"))
        return _YahooSnapshot(
            requested=requested,
            vendor_symbol=vendor_symbol,
            price=price,
            timestamp=timestamp,
            currency=_currency_code(fast.get("currency") or info.get("currency")),
            exchange=_exchange_code(fast.get("exchange") or info.get("exchange") or info.get("fullExchangeName")),
            name=_optional_text(
                info.get("shortName")
                or info.get("longName")
                or _INDEX_NAMES.get(vendor_symbol)
            ),
            bid=_first_finite(info.get("bid"), fast.get("last_bid")),
            ask=_first_finite(info.get("ask"), fast.get("last_ask")),
            change=change,
            change_percent=change_percent,
            volume=_first_finite(
                info.get("regularMarketVolume"),
                fast.get("last_volume"),
                info.get("volume"),
            ),
            average_volume=_first_finite(
                info.get("averageVolume"),
                info.get("averageDailyVolume10Day"),
                fast.get("three_month_average_volume"),
            ),
            asset_class=_asset_class(info.get("quoteType")),
            timezone=_optional_text(
                info.get("exchangeTimezoneName") or fast.get("timezone")
            ),
            trading_hours=_trading_hours(info),
            session=session,
            market_state=_optional_text(info.get("marketState")),
        )

    def _resolve_ticker(self, instrument: str) -> tuple[Any, str]:
        errors: list[str] = []
        for vendor_symbol in _vendor_candidates(instrument):
            try:
                ticker = self._yf().Ticker(vendor_symbol)
                if _ticker_exists(ticker):
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
            raise ProviderError(
                "Yahoo Finance adapter requires the yfinance package."
            ) from exc
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


class _YahooSnapshot:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def _vendor_candidates(instrument: str) -> list[str]:
    token = instrument.strip().upper()
    mapped = _VENDOR_INDEX_TICKERS.get(token)
    if mapped:
        return [mapped]
    candidates = [instrument.strip()]
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


def _ticker_exists(ticker: Any) -> bool:
    try:
        fast = _mapping(getattr(ticker, "fast_info", None))
        if _first_finite(fast.get("last_price"), fast.get("lastPrice")) is not None:
            return True
        info = _mapping(getattr(ticker, "info", None))
        if _first_finite(
            info.get("regularMarketPrice"),
            info.get("currentPrice"),
            info.get("previousClose"),
            info.get("regularMarketPreviousClose"),
        ):
            return True
    except Exception:
        return False
    return False


def _ohlc_prices(frame: Any, symbol: str, period: str, provider: str) -> list[HistoricalPrice]:
    if frame is None or getattr(frame, "empty", True):
        return []
    prices: list[HistoricalPrice] = []
    for index, row in frame.iterrows():
        timestamp = _pandas_timestamp(index)
        open_price = _finite(row.get("Open"))
        high = _finite(row.get("High"))
        low = _finite(row.get("Low"))
        close = _finite(row.get("Close"))
        if timestamp is None or None in {open_price, high, low, close}:
            continue
        try:
            prices.append(
                HistoricalPrice(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    period=period,
                    volume=_finite(row.get("Volume")),
                    source=DataSourceMetadata(
                        provider=provider,
                        source=_SOURCE_NAME,
                        timestamp=timestamp,
                        raw_reference=symbol,
                    ),
                )
            )
        except Exception:
            continue
    return prices


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


def _session(market_state: Any) -> str | None:
    token = _optional_text(market_state)
    if token is None:
        return None
    return _SESSION_BY_MARKET_STATE.get(token.upper())


def _trading_hours(info: dict[str, Any]) -> str | None:
    explicit = _optional_text(info.get("tradingHours") or info.get("regularMarketHours"))
    if explicit:
        return explicit
    start = _optional_text(info.get("regularMarketOpen") or info.get("open"))
    end = _optional_text(info.get("regularMarketClose") or info.get("close"))
    if start and end:
        return f"{start}-{end}"
    return None


def _timestamp(*values: Any) -> datetime | None:
    for value in values:
        parsed = _pandas_timestamp(value)
        if parsed is not None:
            return parsed
    return None


def _pandas_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, (int, float)) and math.isfinite(value):
        if value > 1_000_000_000_000:
            value = value / 1000.0
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    to_pydatetime = getattr(value, "to_pydatetime", None)
    if callable(to_pydatetime):
        return _pandas_timestamp(to_pydatetime())
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


def _asset_class(quote_type: Any) -> str | None:
    token = _optional_text(quote_type)
    if token is None:
        return None
    mapping = {
        "EQUITY": "equity",
        "INDEX": "index",
        "ETF": "etf",
        "MUTUALFUND": "mutual_fund",
        "CRYPTOCURRENCY": "crypto",
        "CURRENCY": "currency",
        "FUTURE": "future",
    }
    return mapping.get(token.upper(), token.lower())


def _public_extra(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in {None, ""}}


def _require_symbol(instrument: str) -> str:
    try:
        return normalize_symbol(instrument)
    except ValueError as exc:
        raise ProviderError("Invalid instrument symbol.") from exc


def _require_interval(interval: str) -> str:
    try:
        return normalize_period(interval)
    except ValueError as exc:
        raise ProviderError("Invalid market interval.") from exc

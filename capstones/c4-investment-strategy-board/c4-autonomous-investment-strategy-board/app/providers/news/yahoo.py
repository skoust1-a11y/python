"""Yahoo Finance news adapter.

Vendor SDK usage stays in this module. Callers depend on `NewsDataProvider`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config.settings import Settings
from app.exceptions import ProviderError
from app.models.common import DataSourceMetadata
from app.models.news import NewsArticle
from app.models.types import normalize_symbol
from app.providers.contracts import NewsDataProvider

logger = logging.getLogger("app.providers.news")
UTC = timezone.utc
_SOURCE_NAME = "yahoo-finance"


class YahooNewsDataProvider(NewsDataProvider):
    """Company and market news headlines via Yahoo Finance."""

    def __init__(self, settings: Settings | None = None, *, client: Any | None = None) -> None:
        self._settings = settings
        self._client = client

    @property
    def name(self) -> str:
        return "yahoo"

    def get_company_news(
        self,
        instrument: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        requested = _require_symbol(instrument)
        ticker, vendor_symbol = self._resolve_ticker(requested)
        try:
            raw_news = list(getattr(ticker, "news", None) or [])
        except Exception as exc:
            raise self._failed(f"Company news for {requested}", exc) from exc

        articles: list[NewsArticle] = []
        for item in raw_news:
            article = _parse_news_item(item, self.name, symbol=requested, vendor_symbol=vendor_symbol)
            if article is None:
                continue
            if start is not None and article.timestamp < start:
                continue
            if end is not None and article.timestamp > end:
                continue
            articles.append(article)
            if len(articles) >= limit:
                break
        return articles

    def get_market_news(
        self,
        *,
        query: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 20,
    ) -> list[NewsArticle]:
        search_query = (query or "").strip()
        yf = self._yf()
        articles: list[NewsArticle] = []
        seen_titles: set[str] = set()

        # Try search news first if query provided or general search
        try:
            target = search_query or "financial markets"
            search = yf.Search(target, news_count=min(limit * 2, 50))
            raw_news = list(getattr(search, "news", None) or [])
        except Exception:
            raw_news = []

        if not raw_news:
            # Fallback to index ticker news
            for index_ticker in ("^NSEI", "^GSPC", "SPY"):
                try:
                    t = yf.Ticker(index_ticker)
                    raw_news.extend(list(getattr(t, "news", None) or []))
                    if len(raw_news) >= limit:
                        break
                except Exception:
                    continue

        for item in raw_news:
            article = _parse_news_item(item, self.name)
            if article is None:
                continue
            if article.headline in seen_titles:
                continue
            seen_titles.add(article.headline)
            if start is not None and article.timestamp < start:
                continue
            if end is not None and article.timestamp > end:
                continue
            articles.append(article)
            if len(articles) >= limit:
                break

        return articles

    def _resolve_ticker(self, instrument: str) -> tuple[Any, str]:
        errors: list[str] = []
        for vendor_symbol in _vendor_candidates(instrument):
            try:
                ticker = self._yf().Ticker(vendor_symbol)
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

    def _failed(self, artifact: str, exc: BaseException) -> ProviderError:
        message = str(exc).strip() or type(exc).__name__
        return ProviderError(f"{artifact} request failed: {message}")


def _vendor_candidates(instrument: str) -> list[str]:
    token = instrument.strip().upper()
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


def _parse_news_item(
    item: Any,
    provider: str,
    *,
    symbol: str | None = None,
    vendor_symbol: str | None = None,
) -> NewsArticle | None:
    if not isinstance(item, dict):
        return None

    # yfinance returns nested {"content": {...}} or flat fields
    content = item.get("content") if isinstance(item.get("content"), dict) else item

    headline = _optional_text(content.get("title") or item.get("title"))
    if not headline:
        return None

    timestamp = _parse_timestamp(
        content.get("pubDate")
        or content.get("displayTime")
        or item.get("providerPublishTime")
        or item.get("pubDate")
    )
    if timestamp is None:
        timestamp = datetime.now(tz=UTC)

    summary = _optional_text(content.get("summary") or content.get("description") or item.get("summary"))

    url_str = None
    canonical = content.get("canonicalUrl") or content.get("clickThroughUrl")
    if isinstance(canonical, dict):
        url_str = _http_url(canonical.get("url"))
    if not url_str:
        url_str = _http_url(content.get("link") or item.get("link") or item.get("url"))

    publisher = None
    provider_dict = content.get("provider") or item.get("provider")
    if isinstance(provider_dict, dict):
        publisher = _optional_text(provider_dict.get("displayName") or provider_dict.get("name"))
    if not publisher:
        publisher = _optional_text(content.get("publisher") or item.get("publisher"))

    source = DataSourceMetadata(
        provider=provider,
        source=_SOURCE_NAME,
        timestamp=timestamp,
        url=url_str or f"https://finance.yahoo.com/quote/{vendor_symbol or symbol or 'news'}",
        raw_reference=vendor_symbol or symbol,
    )

    try:
        return NewsArticle(
            headline=headline,
            timestamp=timestamp,
            source=source,
            summary=summary,
            url=url_str,
            publisher=publisher,
            symbol=symbol,
            extra=_public_extra(
                {
                    "vendor_symbol": vendor_symbol,
                    "id": _optional_text(item.get("id") or content.get("id")),
                }
            ),
        )
    except Exception:
        return None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            return None
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


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _public_extra(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in {None, ""}}


def _require_symbol(instrument: str) -> str:
    try:
        return normalize_symbol(instrument)
    except ValueError as exc:
        raise ProviderError("Invalid instrument symbol.") from exc

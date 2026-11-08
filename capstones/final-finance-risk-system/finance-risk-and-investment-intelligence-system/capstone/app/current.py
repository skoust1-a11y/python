"""Live quotes/news for evidence_mode=current.

Cursor MCP servers (yahoo-finance, nse-bse, chittorgarh) are IDE-only.
This module uses the same backends in-process: Yahoo Finance HTTP for
quotes/news (US + NSE/BSE suffixes), Chittorgarh client for IPO/GMP.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

from app.core.config import get_settings

_UA = "FinanceRiskCapstone/0.4 (educational; quotes+news)"
_EXPLICIT = re.compile(r"\b[A-Z]{1,15}(?:\.[A-Z]{1,3})?\b")
_IPO = re.compile(r"\b(ipos?|gmp|grey[- ]market|ncds?|buybacks?|subscription)\b", re.I)
_INDIA = re.compile(r"\b(nse|bse|nifty|sensex|india|indian)\b", re.I)

# Seeded names + common Indian aliases. Values are Yahoo symbols.
_ALIASES = {
    "apple": "AAPL",
    "apple inc": "AAPL",
    "aapl": "AAPL",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "amazon": "AMZN",
    "amzn": "AMZN",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "googl": "GOOGL",
    "goog": "GOOG",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "jpm": "JPM",
    "gold etf": "GLD",
    "gld": "GLD",
    "oil futures": "USO",
    "uso": "USO",
    "us treasury bonds": "TLT",
    "tlt": "TLT",
    "emerging market etf": "EEM",
    "eem": "EEM",
    "corporate bond fund": "LQD",
    "lqd": "LQD",
    "reliance": "RELIANCE.NS",
    "reliance industries": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "icicibank": "ICICIBANK.NS",
    "sbi": "SBIN.NS",
    "sbin": "SBIN.NS",
    "itc": "ITC.NS",
    "bharti": "BHARTIARTL.NS",
    "bharti airtel": "BHARTIARTL.NS",
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "sensex": "^BSESN",
    "sp500": "^GSPC",
    "s&p 500": "^GSPC",
    "nasdaq": "^IXIC",
}

_SKIP_TICKERS = {
    "US", "EU", "UK", "GDP", "CEO", "ETF", "IPO", "GMP", "NCD", "NSE", "BSE",
    "SQL", "RAG", "HIGH", "LOW", "FY", "THE", "AND", "FOR", "ARE", "NOT",
    "ALL", "ANY", "OUR", "THIS", "THAT", "WITH", "FROM", "INTO",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _provider_for(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith(".NS") or upper in {"^NSEI"}:
        return "nse"
    if upper.endswith(".BO") or upper in {"^BSESN"}:
        return "bse"
    return "yahoo"


def _resolve_name(name: str) -> Optional[str]:
    raw = (name or "").strip()
    if not raw:
        return None
    key = re.sub(r"\s+", " ", raw.lower())
    if key in _ALIASES:
        return _ALIASES[key]
    compact = key.replace(" ", "")
    if compact in _ALIASES:
        return _ALIASES[compact]
    token = raw.upper()
    if token.startswith("^") and 2 <= len(token) <= 12:
        return token
    if re.fullmatch(r"[A-Z]{1,15}\.(NS|BO|L)", token):
        return token
    if re.fullmatch(r"[A-Z]{1,5}", token) and token not in _SKIP_TICKERS:
        return token
    return None


def resolve_symbols(query: str, sql_evidence: Sequence[Dict[str, Any]] | None = None) -> List[str]:
    found: List[str] = []

    def add(symbol: Optional[str]) -> None:
        if symbol and symbol not in found:
            found.append(symbol)

    blob = query or ""
    lower = blob.lower()
    for alias, symbol in sorted(_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", lower):
            add(symbol)
    for match in _EXPLICIT.finditer(blob):
        add(_resolve_name(match.group(0)))
    for block in sql_evidence or []:
        for row in block.get("rows") or []:
            add(_resolve_name(str(row.get("asset_name") or "")))
    if _INDIA.search(blob) and "^NSEI" not in found:
        found.append("^NSEI")
    return found[:8]


def _quote_from_chart(symbol: str, payload: Dict[str, Any], stale_after: int) -> Optional[Dict[str, Any]]:
    results = ((payload or {}).get("chart") or {}).get("result") or []
    if not results:
        return None
    meta = results[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    if price is None:
        return None
    stamp = meta.get("regularMarketTime")
    as_of = datetime.fromtimestamp(int(stamp), tz=timezone.utc) if stamp else _now()
    age = (_now() - _as_aware(as_of)).total_seconds()
    resolved = str(meta.get("symbol") or symbol)
    return {
        "type": "quote",
        "symbol": resolved,
        "price": float(price),
        "as_of": as_of,
        "provider_id": _provider_for(resolved),
        "stale": age > stale_after,
    }


def _news_from_search(payload: Dict[str, Any], max_age: timedelta, limit: int) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    cutoff = _now() - max_age
    for row in (payload or {}).get("news") or []:
        headline = (row.get("title") or "").strip()
        url = (row.get("link") or "").strip()
        if not headline or not url:
            continue
        stamp = row.get("providerPublishTime")
        published = datetime.fromtimestamp(int(stamp), tz=timezone.utc) if stamp else _now()
        if published < cutoff:
            continue
        items.append(
            {
                "type": "news",
                "headline": headline[:300],
                "source": str(row.get("publisher") or "Yahoo Finance"),
                "url": url,
                "published_at": published,
                "provider_id": "yahoo",
            }
        )
        if len(items) >= limit:
            break
    return items


def _http_get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with httpx.Client(
        timeout=get_settings().market_http_timeout_s,
        headers={"User-Agent": _UA, "Accept": "application/json"},
    ) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def fetch_quotes(symbols: Sequence[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    settings = get_settings()
    quotes: List[Dict[str, Any]] = []
    gaps: List[str] = []

    def one(symbol: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            payload = _http_get(
                get_settings().yahoo_chart_url.format(symbol=symbol),
                {"interval": "1d", "range": "1d"},
            )
            quote = _quote_from_chart(symbol, payload, settings.market_max_stale_seconds)
            if quote is None:
                return None, "No live quote for {}".format(symbol)
            return quote, None
        except Exception:
            return None, "Quote provider failed for {}".format(symbol)

    if not symbols:
        return quotes, gaps
    with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as pool:
        for quote, gap in pool.map(one, symbols):
            if quote:
                quotes.append(quote)
            if gap:
                gaps.append(gap)
    return quotes, gaps


def fetch_news(topics: Sequence[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    settings = get_settings()
    max_age = timedelta(hours=settings.news_max_age_hours)
    news: List[Dict[str, Any]] = []
    gaps: List[str] = []
    seen: set[str] = set()

    def one(topic: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        try:
            payload = _http_get(
                get_settings().yahoo_search_url,
                {"q": topic, "quotesCount": 0, "newsCount": 6, "enableFuzzyQuery": "false"},
            )
            return _news_from_search(payload, max_age, 4), None
        except Exception:
            return [], "News provider failed for {}".format(topic)

    queries = [item for item in topics if item][:4]
    if not queries:
        return news, gaps
    with ThreadPoolExecutor(max_workers=min(4, len(queries))) as pool:
        for items, gap in pool.map(one, queries):
            if gap:
                gaps.append(gap)
            for item in items:
                key = item["url"]
                if key in seen:
                    continue
                seen.add(key)
                news.append(item)
    return news[:8], gaps


def _row_dict(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        return row
    if hasattr(row, "__dict__"):
        return {k: v for k, v in vars(row).items() if not k.startswith("_")}
    return {"value": row}


def _field(row: Dict[str, Any], *names: str) -> Any:
    lower = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lower and lower[name.lower()] not in (None, ""):
            return lower[name.lower()]
    return None


def fetch_chittorgarh(query: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not _IPO.search(query or ""):
        return [], []
    try:
        from chittorgarh_client.client import ChittorgarhClient, InvestorGainClient
    except ImportError:
        return [], ["Chittorgarh client is not installed"]

    items: List[Dict[str, Any]] = []
    gaps: List[str] = []
    now = _now()

    def add_rows(rows: Iterable[Any], source: str, url_fallback: str) -> None:
        for row in list(rows)[:5]:
            data = _row_dict(row)
            name = _field(data, "name", "company_name", "company", "ipo_name") or source
            extra = _field(data, "gmp", "status", "subscription", "open", "open_date")
            headline = "{}".format(name) if extra is None else "{} · {}".format(name, extra)
            link = str(_field(data, "url", "link") or url_fallback)
            items.append(
                {
                    "type": "news",
                    "headline": headline[:300],
                    "source": "Chittorgarh",
                    "url": link,
                    "published_at": now,
                    "provider_id": "chittorgarh",
                }
            )

    try:
        client = ChittorgarhClient()
        q = (query or "").lower()
        if "sme" in q:
            add_rows(client.get_sme_ipos(), "SME IPO", "https://www.chittorgarh.com/ipo/ipo_list.asp")
        elif re.search(r"\bncds?\b", q):
            add_rows(client.get_ncds(), "NCD", "https://www.chittorgarh.com/")
        elif "buyback" in q:
            add_rows(client.get_buy_backs(), "Buyback", "https://www.chittorgarh.com/")
        else:
            add_rows(client.get_mainboard_ipos(), "Mainboard IPO", "https://www.chittorgarh.com/ipo/ipo_list.asp")
        if "gmp" in q or "grey" in q:
            add_rows(InvestorGainClient().get_mainboard_ipos(), "IPO GMP", "https://www.chittorgarh.com/")
    except Exception:
        gaps.append("Chittorgarh provider failed")
    return items[:6], gaps


def collect_current(
    query: str,
    sql_evidence: Sequence[Dict[str, Any]] | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    symbols = resolve_symbols(query, sql_evidence)
    topics: List[str] = list(symbols)
    if query and query.strip() not in topics:
        topics.append(query.strip()[:80])
    quotes, qgaps = fetch_quotes(symbols)
    news, ngaps = fetch_news(topics[:3] if topics else [query])
    ipo, igaps = fetch_chittorgarh(query)
    news.extend(ipo)
    gaps = qgaps + ngaps + igaps
    if not quotes and not news:
        gaps.append("No live quote or headline was retrieved")
    return quotes, news, gaps

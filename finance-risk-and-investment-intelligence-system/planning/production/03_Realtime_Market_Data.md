# Production — Current factors (quotes + news)

Live enrichment is **opt-in per query**. Default remains documents + SQL (`evidence_mode=corpus`).

## User switch

| UI label | `options.evidence_mode` | Sources |
|---|---|---|
| Documents only | `corpus` | Policy / workspace docs + SQL |
| Documents + current | `current` | Corpus **plus** quotes/fundamentals **plus** headlines |

`GET /auth/me` → `features.current_factors` enables the second option. If false, UI disables it; API returns **409** `current_factors_unavailable`.

Capstone never turns this on. Golden set always uses `corpus`.

## Adapters

```
ProviderAdapter
  get_quotes(symbols)
  get_fundamentals(symbols)
  stream_quotes(symbols)   # optional WebSocket

NewsAdapter
  get_headlines(symbols_or_topics, since)
```

Implementations: HTTP poll / WebSocket; vendors such as Polygon, Refinitiv, Finnhub, NewsAPI. Credentials only in secret manager. No scraping.

## Rules

- `current` still runs corpus retrieval + SQL first. Adapters **enrich**; they do not replace docs.
- Every market number carries `as_of` + `provider_id`. Age > `MARKET_MAX_STALE_SECONDS` → label **stale** or escalate. Never invent a price.
- Every headline carries `published_at` + source + URL. Age > `NEWS_MAX_AGE_HOURS` → drop or label stale. Never invent a headline.
- Rate limits and symbol allow-lists live in the adapter, not the prompt.
- Synthesis stays tool-less; it only sees the evidence bundle (`doc` / `sql` / `quote` / `news`).

## Config (production deploy only)

```
CURRENT_FACTORS_ENABLED=true
MARKET_PROVIDER=...
NEWS_PROVIDER=...
MARKET_POLL_SECONDS=5
MARKET_MAX_STALE_SECONDS=60
NEWS_MAX_AGE_HOURS=24
```

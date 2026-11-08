"""News provider adapters.

Services depend on `NewsDataProvider`. Concrete vendors are selected by
`NEWS_PROVIDER` through `build_news_data_provider`.
"""

from app.providers.news.factory import (
    NEWS_ADAPTERS,
    build_news_data_provider,
    normalize_news_provider,
)

__all__ = [
    "NEWS_ADAPTERS",
    "build_news_data_provider",
    "normalize_news_provider",
]

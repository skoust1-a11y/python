from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import date
from threading import Lock
from typing import Deque, Dict

from prometheus_client import Counter

from app.core.config import get_settings

COST = Counter("frii_cost_usd_total", "Estimated LLM spend in USD")

_lock = Lock()
_spend: Dict[str, float] = {}
_day = date.today()
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _roll_day() -> None:
    global _day
    today = date.today()
    if today != _day:
        _spend.clear()
        _day = today


def record_cost(user_id: str, cost_usd: float) -> None:
    amount = max(float(cost_usd), 0.0)
    with _lock:
        _roll_day()
        _spend[user_id] = _spend.get(user_id, 0.0) + amount
    if amount:
        COST.inc(amount)


def reset() -> None:
    with _lock:
        _spend.clear()
        _hits.clear()


def spent_today(user_id: str) -> float:
    with _lock:
        _roll_day()
        return _spend.get(user_id, 0.0)


def budget_ok(user_id: str, extra: float = 0.0) -> bool:
    settings = get_settings()
    if not settings.cost_tracking_enabled:
        return True
    if settings.daily_budget_usd <= 0:
        return False
    return spent_today(user_id) + extra <= settings.daily_budget_usd


def tokens_ok(total: int) -> bool:
    return total <= get_settings().max_tokens_per_request


def rate_ok(user_id: str) -> bool:
    settings = get_settings()
    now = time.time()
    with _lock:
        q = _hits[user_id]
        while q and now - q[0] > settings.rate_window_seconds:
            q.popleft()
        if len(q) >= settings.rate_limit_per_minute:
            return False
        q.append(now)
        return True

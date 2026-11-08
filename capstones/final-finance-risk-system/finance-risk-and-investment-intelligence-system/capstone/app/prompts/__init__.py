from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings

_DIR = Path(__file__).parent
_SETTINGS_TOKENS = (
    "risk_score_medium",
    "risk_score_high",
    "risk_score_escalation",
    "confidence_escalation_floor",
    "stale_high_risk_days",
    "retrieval_min_score",
    "sector_allocation_cap",
    "emerging_market_cap",
)

REQUIRED = (
    "router.md",
    "retrieval.md",
    "portfolio_eval.md",
    "market_data.md",
    "risk.md",
    "synthesis.md",
    "synthesis_stock.md",
    "escalation.md",
    "refusals/insufficient_evidence.md",
    "refusals/override_refusal.md",
    "refusals/non_advice.md",
)


def load(name: str) -> str:
    path = _DIR / name
    if not path.suffix:
        path = _DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    settings = get_settings()
    for key in _SETTINGS_TOKENS:
        text = text.replace("{{" + key + "}}", str(getattr(settings, key)))
    return text


def catalog() -> dict[str, str]:
    return {name: load(name) for name in REQUIRED}

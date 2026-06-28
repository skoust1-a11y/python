"""Detect factual claims not grounded in retrieved source excerpts."""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional

from guardrails.validators import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)

from app.guardrails.constants import INSUFFICIENT_INFO_PHRASES

_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(r"\$[\d,]+(?:\.\d{2})?")
_PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?%")
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")


def _source_corpus(metadata: Dict) -> str:
    excerpts: list[str] = []
    for source in metadata.get("sources") or []:
        if isinstance(source, dict):
            excerpts.append(str(source.get("excerpt", "")))
            label = source.get("citation_label")
            if label:
                excerpts.append(str(label))
    return " ".join(excerpts).lower()


def _is_insufficient_info_response(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in INSUFFICIENT_INFO_PHRASES)


def _extract_claim_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for pattern in (_DATE_RE, _MONEY_RE, _PERCENT_RE):
        tokens.extend(match.group(0) for match in pattern.finditer(text))
    tokens.extend(match.group(0) for match in _PROPER_NOUN_RE.finditer(text))
    return list(dict.fromkeys(tokens))


def _token_in_corpus(token: str, corpus: str) -> bool:
    normalized = token.lower().strip()
    if not normalized:
        return True
    if normalized in corpus:
        return True
    # Allow partial matches for multi-word proper nouns.
    words = normalized.split()
    if len(words) > 1 and all(word in corpus for word in words):
        return True
    return False


@register_validator(name="legal/unsupported-claims", data_type="string")
class UnsupportedClaimDetector(Validator):
    """Flag specific factual claims that do not appear in retrieved sources."""

    def __init__(
        self,
        min_unsupported: int = 1,
        on_fail: Optional[Callable] = None,
    ) -> None:
        super().__init__(on_fail=on_fail, min_unsupported=min_unsupported)
        self.min_unsupported = min_unsupported

    def _validate(self, value: str, metadata: Dict) -> ValidationResult:
        if _is_insufficient_info_response(value):
            return PassResult()

        corpus = _source_corpus(metadata)
        if not corpus.strip():
            return PassResult()

        unsupported = [
            token
            for token in _extract_claim_tokens(value)
            if not _token_in_corpus(token, corpus)
        ]

        if len(unsupported) >= self.min_unsupported:
            sample = ", ".join(unsupported[:3])
            return FailResult(
                error_message=(
                    f"Response contains unsupported factual claims not found in "
                    f"retrieved sources: {sample}"
                ),
            )

        return PassResult()

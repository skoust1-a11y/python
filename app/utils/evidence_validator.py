"""Pre-synthesis validation for retrieved document evidence quality.

Regression note (2026): A shared post-retrieval gate was introduced that (1) skipped
Evidence-mode LLM extraction and (2) stripped sources before guardrails when
validation failed. Scenario questions often spread vocabulary across chunks and
use hypothetical phrasing ("what happens if…", "can a tenant…") that the original
regex/topic rules did not recognise, causing false negatives. Validation here
controls Evidence-mode LLM gating and confidence only — retrieved sources must
remain available to Explain mode and guardrails regardless of this outcome.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_/']*")
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "under",
        "over",
        "and",
        "or",
        "but",
        "if",
        "then",
        "than",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "not",
        "only",
        "own",
        "same",
        "so",
        "too",
        "very",
        "just",
        "about",
        "any",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "they",
        "their",
        "he",
        "she",
        "his",
        "her",
        # Conversational / request verbs (not document topics)
        "tell",
        "say",
        "describe",
        "give",
        "show",
        "know",
        "find",
        "look",
        "want",
        "need",
        "help",
        "please",
        "get",
        "list",
        "explain",
        "summarize",
        "summary",
        "overview",
        "information",
        "info",
        "details",
        "detail",
        "speak",
        "talk",
        "share",
    }
)

_GENERIC_QUERY_TERMS = frozenset(
    {
        "role",
        "party",
        "parties",
        "agreement",
        "contract",
        "clause",
        "clauses",
        "term",
        "terms",
        "payment",
        "notice",
        "termination",
        "liability",
        "law",
        "legal",
        "document",
        "documents",
        "section",
        "provision",
        "provisions",
        "amount",
        "fee",
        "fees",
        "gst",
        "tax",
        "vat",
        "inclusive",
        "exclusive",
        "price",
        "pricing",
        "cost",
        "day",
        "days",
        "late",
        "apply",
        "applies",
        "total",
        "period",
        "date",
        "year",
        "month",
        "service",
        "services",
        "right",
        "rights",
        "obligation",
        "obligations",
        "warranty",
        "warranties",
        "include",
        "including",
        "employee",
        "tenant",
        "landlord",
        "resign",
        "resignation",
        "terminate",
        "circumstances",
        "delayed",
        "delay",
        "penalty",
        "penalties",
        "resigns",
    }
)

# Common question openers — capitalized at sentence start, not entity names.
_SENTENCE_START_WORDS = frozenset(
    {
        "what",
        "who",
        "when",
        "where",
        "why",
        "how",
        "tell",
        "is",
        "are",
        "can",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "if",
    }
)

_SCENARIO_QUESTION_RE = re.compile(
    r"\b(?:"
    r"if\b|what\s+if|what\s+happens|suppose|assuming|calculate|how\s+much|"
    r"should\s+i\s+pay|inclusive\s+or\s+exclusive|goods\s+worth|"
    r"total\s+(?:amount|cost|due)|including\s+.+\s+and|"
    r"can\s+(?:a|an|the)\b|under\s+what|in\s+what\s+circumstances|"
    r"without\s+notice|(?:resign|terminate|termination)"
    r")\b",
    re.IGNORECASE,
)

# Tax/pricing terms — matching any one in a chunk is enough for direct relevance.
_PRIMARY_TOPIC_TERMS = frozenset(
    {
        "gst",
        "tax",
        "vat",
        "payment",
        "fee",
        "fees",
        "inclusive",
        "exclusive",
        "price",
        "pricing",
        "cost",
    }
)

_NUMERIC_QUERY_TERM_RE = re.compile(r"^\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Outcome of shared post-retrieval evidence validation."""

    sufficient: bool
    relevance: float


def _normalize_retrieval_score(score: float) -> float:
    """Map cosine, SQL fixed, and RRF scores onto a common 0-1 scale."""
    if score <= 0.0:
        return 0.0
    if score < 0.15:
        return min(score * 20.0, 1.0)
    return min(score, 1.0)


def _source_semantic_score(source: dict[str, Any]) -> float:
    """
    Return the raw retrieval similarity for a source.

    Post-ranking scores include keyword and same-document boosts; validation
    must use semantic similarity so weak matches are not treated as strong.
    """
    metadata = source.get("metadata")
    if isinstance(metadata, dict):
        semantic = metadata.get("semantic_score")
        if semantic is not None:
            return float(semantic)
    return float(source.get("score") or 0.0)


def _rank_weighted_relevance(sources: list[dict[str, Any]]) -> float:
    scores = [_normalize_retrieval_score(_source_semantic_score(source)) for source in sources]
    if not scores:
        return 0.0
    weights = [1.0 / (index + 1) for index in range(len(scores))]
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    normalized = weighted_sum / total_weight if total_weight else 0.0
    return round(min(max(normalized, 0.0), 1.0), 4)


def _extract_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(query):
        term = match.group(0).lower()
        if len(term) < 2 or term in _STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms


def _extract_proper_noun_terms(question: str) -> list[str]:
    """
    Terms that look like named entities (capitalized in the question).

    Used only to block hallucinated answers about specific people or topics
    that do not appear in the corpus. Generic legal-topic questions rely on
    semantic similarity and keyword overlap instead.
    """
    terms: list[str] = []
    seen: set[str] = set()
    matches = list(_TOKEN_RE.finditer(question))
    for index, match in enumerate(matches):
        raw = match.group(0)
        lowered = raw.lower()
        if len(lowered) < 2 or lowered in _STOP_WORDS or lowered in seen:
            continue
        if not raw[0].isupper():
            continue
        if index == 0 and lowered in _SENTENCE_START_WORDS:
            continue
        seen.add(lowered)
        terms.append(lowered)
    return terms


def _legal_topic_overlap(query_terms: list[str], sources: list[dict[str, Any]]) -> float:
    """Overlap on document-topic terms (payment, termination, etc.)."""
    topic_terms = [term for term in query_terms if term in _GENERIC_QUERY_TERMS]
    if not topic_terms:
        return 0.0
    return _max_topic_overlap(topic_terms, sources)


def _collective_topic_overlap(query_terms: list[str], sources: list[dict[str, Any]]) -> float:
    """Share of topic terms found across all retrieved chunks (multi-clause scenarios)."""
    topic_terms = [term for term in query_terms if term in _GENERIC_QUERY_TERMS]
    if not topic_terms:
        return 0.0
    return _collective_topic_hits(topic_terms, sources) / len(topic_terms)


def _is_scenario_question(question: str, query_terms: list[str]) -> bool:
    """Hypothetical multi-clause questions spread evidence across several chunks."""
    if not _SCENARIO_QUESTION_RE.search(question):
        return False
    topic_count = sum(1 for term in query_terms if term in _GENERIC_QUERY_TERMS)
    # A single domain term plus hypothetical phrasing is enough (e.g. "if payment is delayed").
    return topic_count >= 1


def _overlap_query_terms(query_terms: list[str]) -> list[str]:
    """Query terms for corpus overlap, excluding hypothetical numeric amounts."""
    return [term for term in query_terms if not _NUMERIC_QUERY_TERM_RE.match(term)]


def _chunk_text(source: dict[str, Any]) -> str:
    return source.get("full_text") or source.get("excerpt") or ""


def _term_in_text(term: str, text: str) -> bool:
    if not term or not text:
        return False
    pattern = re.compile(
        rf"(?<![A-Za-z0-9\-_/']){re.escape(term)}(?![A-Za-z0-9\-_/'])",
        re.IGNORECASE,
    )
    return pattern.search(text) is not None


def _topic_term_in_text(term: str, text: str) -> bool:
    """Topic overlap allows simple singular/plural variants (fee/fees)."""
    for variant in _term_variants(term):
        if _term_in_text(variant, text):
            return True
    return False


def _term_variants(term: str) -> list[str]:
    """Simple singular/plural variants for legal-topic overlap (fee/fees)."""
    variants = [term]
    if term.endswith("s") and len(term) > 3:
        variants.append(term[:-1])
    elif not term.endswith("s"):
        variants.append(f"{term}s")
    return variants


def _max_topic_overlap(topic_terms: list[str], sources: list[dict[str, Any]]) -> float:
    if not topic_terms:
        return 0.0

    best = 0.0
    for source in sources:
        text = _chunk_text(source)
        if not text:
            continue
        hits = sum(1 for term in topic_terms if _topic_term_in_text(term, text))
        best = max(best, hits / len(topic_terms))
    return best


def _collective_topic_hits(topic_terms: list[str], sources: list[dict[str, Any]]) -> int:
    combined_text = " ".join(_chunk_text(source) for source in sources)
    if not combined_text.strip():
        return 0
    return sum(1 for term in topic_terms if _topic_term_in_text(term, combined_text))


def _max_query_overlap(query_terms: list[str], sources: list[dict[str, Any]]) -> float:
    if not query_terms:
        return 1.0

    best = 0.0
    for source in sources:
        text = _chunk_text(source)
        if not text:
            continue
        hits = sum(1 for term in query_terms if _term_in_text(term, text))
        best = max(best, hits / len(query_terms))
    return best


def _collective_query_overlap(query_terms: list[str], sources: list[dict[str, Any]]) -> float:
    """Share of query terms found across all chunks (multi-clause scenarios)."""
    if not query_terms:
        return 1.0
    combined_text = " ".join(_chunk_text(source) for source in sources)
    if not combined_text.strip():
        return 0.0
    hits = sum(1 for term in query_terms if _term_in_text(term, combined_text))
    return hits / len(query_terms)


def _has_entity_grounding(
    entity_terms: list[str],
    sources: list[dict[str, Any]],
) -> bool:
    if not entity_terms:
        return True
    return any(
        _term_in_text(term, _chunk_text(source))
        for source in sources
        for term in entity_terms
    )


def validate_retrieved_evidence(
    question: str,
    sources: list[dict[str, Any]],
    *,
    relevance_threshold: float | None = None,
    min_chunk_similarity: float | None = None,
    query_overlap_threshold: float | None = None,
) -> EvidenceValidationResult:
    """
    Shared post-retrieval gate used by every response mode.

    Determines whether retrieved chunks contain enough factual support to
    present evidence or generate grounded answers.
    """
    if not sources:
        return EvidenceValidationResult(sufficient=False, relevance=0.0)

    relevance_floor = (
        relevance_threshold
        if relevance_threshold is not None
        else settings.EVIDENCE_RELEVANCE_THRESHOLD
    )
    min_similarity = (
        min_chunk_similarity
        if min_chunk_similarity is not None
        else settings.EVIDENCE_MIN_CHUNK_SIMILARITY
    )
    overlap_floor = (
        query_overlap_threshold
        if query_overlap_threshold is not None
        else settings.EVIDENCE_QUERY_OVERLAP_THRESHOLD
    )

    relevance = _rank_weighted_relevance(sources)
    if relevance < relevance_floor:
        return EvidenceValidationResult(sufficient=False, relevance=relevance)

    normalized_scores = [
        _normalize_retrieval_score(_source_semantic_score(source)) for source in sources
    ]
    best_score = max(normalized_scores) if normalized_scores else 0.0
    query_terms = _extract_query_terms(question)
    topic_overlap = _legal_topic_overlap(query_terms, sources)
    collective_topic_overlap = _collective_topic_overlap(query_terms, sources)
    scenario_question = _is_scenario_question(question, query_terms)

    # Strong on-topic keyword overlap (e.g. "payment terms") can justify evidence
    # when cosine similarity is moderate — matches pre-fix practical behavior.
    # Multi-clause scenario questions use collective coverage across chunks.
    similarity_floor = min_similarity
    if (
        topic_overlap >= 0.5
        or collective_topic_overlap >= 0.5
        or (scenario_question and collective_topic_overlap >= 0.4)
    ):
        similarity_floor = min(min_similarity, 0.28)

    if best_score < similarity_floor:
        return EvidenceValidationResult(sufficient=False, relevance=relevance)

    overlap_terms = _overlap_query_terms(query_terms)
    effective_overlap_floor = overlap_floor
    if topic_overlap >= 0.5 or collective_topic_overlap >= 0.5 or scenario_question:
        effective_overlap_floor = min(overlap_floor, 0.10)

    if overlap_terms:
        per_chunk_overlap = _max_query_overlap(overlap_terms, sources)
        overlap_ok = per_chunk_overlap >= effective_overlap_floor
        if not overlap_ok and scenario_question:
            collective_overlap = _collective_query_overlap(overlap_terms, sources)
            overlap_ok = collective_overlap >= effective_overlap_floor
        if not overlap_ok:
            return EvidenceValidationResult(sufficient=False, relevance=relevance)

    entity_terms = _extract_proper_noun_terms(question)
    if not _has_entity_grounding(entity_terms, sources):
        return EvidenceValidationResult(sufficient=False, relevance=relevance)

    # Off-topic queries with no legal-topic overlap still need strong similarity.
    if not entity_terms and topic_overlap < overlap_floor and best_score < min_similarity:
        return EvidenceValidationResult(sufficient=False, relevance=relevance)

    return EvidenceValidationResult(sufficient=True, relevance=relevance)


def filter_public_sources(
    sources: list[dict[str, Any]],
    *,
    evidence_sufficient: bool,
) -> list[dict[str, Any]]:
    """Return retrieved sources for API responses.

    Sources are kept whenever retrieval returned chunks. Hiding them when
    ``evidence_sufficient`` is false caused Explain-mode guardrails to run with
    an empty corpus (blocking scenario answers) and made related provisions
    invisible in Evidence mode. ``evidence_sufficient`` affects strict-mode LLM
    gating and confidence metrics only.
    """
    return list(sources)


def _is_pricing_question(question: str, query_terms: list[str]) -> bool:
    """GST, fee, and pay-amount questions need pricing-related chunks."""
    lowered = question.lower()
    if re.search(r"inclusive\s+or\s+exclusive", lowered):
        return True
    if re.search(r"should\s+i\s+pay", lowered):
        return True
    pricing_terms = {"gst", "inclusive", "exclusive", "price", "pricing", "cost", "fee", "fees", "pay"}
    return bool(pricing_terms & set(query_terms))


def is_directly_relevant(question: str, text: str) -> bool:
    """
    True when chunk text explicitly addresses the question topic (Evidence Direct).

    Indirect clauses — needed for scenarios but not explicitly on-topic — are excluded.
    """
    if not text or not text.strip():
        return False

    query_terms = _extract_query_terms(question)
    entity_terms = _extract_proper_noun_terms(question)

    if entity_terms:
        return any(_term_in_text(term, text) for term in entity_terms)

    overlap_terms = _overlap_query_terms(query_terms)
    if not overlap_terms:
        return False

    topic_terms = [term for term in overlap_terms if term in _GENERIC_QUERY_TERMS]
    specific_terms = [term for term in overlap_terms if term not in _GENERIC_QUERY_TERMS]

    if specific_terms and any(_term_in_text(term, text) for term in specific_terms):
        return True

    if _is_pricing_question(question, overlap_terms):
        if any(_topic_term_in_text(term, text) for term in _PRIMARY_TOPIC_TERMS):
            return True

    if topic_terms:
        for term in topic_terms:
            if term in _PRIMARY_TOPIC_TERMS and _topic_term_in_text(term, text):
                return True
        hits = sum(1 for term in topic_terms if _topic_term_in_text(term, text))
        return (hits / len(topic_terms)) >= 0.5

    return any(_term_in_text(term, text) for term in overlap_terms)


def filter_direct_sources(
    question: str,
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only chunks whose text explicitly addresses the question topic."""
    return [
        source
        for source in sources
        if is_directly_relevant(question, _chunk_text(source))
    ]


def has_sufficient_evidence(
    question: str,
    sources: list[dict[str, Any]],
    *,
    relevance_threshold: float | None = None,
    min_chunk_similarity: float | None = None,
    query_overlap_threshold: float | None = None,
) -> bool:
    """
    Decide whether retrieved chunks justify Evidence-mode extraction.

    Returns False when retrieval quality is too low to present supporting
    clauses — e.g. completely off-topic questions that still return chunks.
    """
    return validate_retrieved_evidence(
        question,
        sources,
        relevance_threshold=relevance_threshold,
        min_chunk_similarity=min_chunk_similarity,
        query_overlap_threshold=query_overlap_threshold,
    ).sufficient

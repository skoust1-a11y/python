"""Compress retrieved context before LLM synthesis while preserving citations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import settings
from app.utils.tokens import count_tokens
from app.rag.context_builder import BuiltContext
from app.rag.ranking import extract_query_terms

_BLOCK_SEPARATOR = "\n\n---\n\n"
_HEADER_PATTERN = re.compile(
    r"^(\[Source \d+\])(?:\s+\[[^\]]+\])?\s+\(document=[^,]+,\s*chunk=[^\)]+\)\s*$",
    re.MULTILINE,
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class ContextBlock:
    """A single citable context block with header and body text."""

    citation_label: str
    header_line: str
    body: str
    score: float


@dataclass(frozen=True)
class CompressionStats:
    """Diagnostics from context compression."""

    enabled: bool
    original_tokens: int
    compressed_tokens: int
    blocks_input: int
    blocks_output: int
    duplicate_sentences_removed: int
    irrelevant_sentences_removed: int
    overlaps_merged: int

    @property
    def tokens_saved(self) -> int:
        return max(0, self.original_tokens - self.compressed_tokens)

    @property
    def reduction_ratio(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return round(1.0 - (self.compressed_tokens / self.original_tokens), 4)


@dataclass(frozen=True)
class CompressedContext:
    """Compressed prompt context ready for synthesis."""

    context_text: str
    stats: CompressionStats


class ContextCompressionService:
    """Reduce LLM context size by deduplicating, merging overlaps, and filtering noise."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        max_context_tokens: int | None = None,
        relevance_threshold: float | None = None,
        near_duplicate_jaccard_threshold: float | None = None,
        min_sentence_chars: int | None = None,
    ) -> None:
        self._enabled = (
            settings.ENABLE_CONTEXT_COMPRESSION if enabled is None else enabled
        )
        self._max_context_tokens = max_context_tokens or settings.MAX_CONTEXT_TOKENS
        self._relevance_threshold = (
            relevance_threshold
            if relevance_threshold is not None
            else settings.CONTEXT_COMPRESSION_RELEVANCE_THRESHOLD
        )
        self._near_duplicate_jaccard_threshold = (
            near_duplicate_jaccard_threshold
            if near_duplicate_jaccard_threshold is not None
            else settings.CONTEXT_COMPRESSION_NEAR_DUPLICATE_JACCARD_THRESHOLD
        )
        self._min_sentence_chars = (
            min_sentence_chars
            if min_sentence_chars is not None
            else settings.CONTEXT_COMPRESSION_MIN_SENTENCE_CHARS
        )

    def compress(
        self,
        built_context: BuiltContext,
        question: str,
    ) -> CompressedContext:
        """Return minimal context required for accurate, citable answers."""
        original_text = built_context.context_text
        original_tokens = count_tokens(original_text)

        if not self._enabled or not original_text.strip():
            return CompressedContext(
                context_text=original_text,
                stats=CompressionStats(
                    enabled=self._enabled,
                    original_tokens=original_tokens,
                    compressed_tokens=original_tokens,
                    blocks_input=len(built_context.sources),
                    blocks_output=len(built_context.sources),
                    duplicate_sentences_removed=0,
                    irrelevant_sentences_removed=0,
                    overlaps_merged=0,
                ),
            )

        blocks = _parse_context_blocks(original_text, built_context)
        query_terms = extract_query_terms(question)

        compressed_blocks: list[ContextBlock] = []
        seen_sentence_keys: set[str] = set()
        duplicate_sentences_removed = 0
        irrelevant_sentences_removed = 0
        overlaps_merged = 0

        for block in blocks:
            boundary_compacted, boundary_merges = _compact_boundary_overlaps(block.body)
            overlaps_merged += boundary_merges
            sentences = _split_sentences(boundary_compacted)
            kept_sentences: list[str] = []

            for sentence in sentences:
                normalized = _normalize_sentence(sentence)
                if len(normalized) < self._min_sentence_chars:
                    kept_sentences.append(sentence)
                    continue

                if _is_duplicate_sentence(
                    normalized,
                    seen_sentence_keys,
                    self._near_duplicate_jaccard_threshold,
                ):
                    duplicate_sentences_removed += 1
                    continue

                if query_terms and not _is_relevant_sentence(
                    normalized,
                    query_terms,
                    self._relevance_threshold,
                ):
                    irrelevant_sentences_removed += 1
                    continue

                seen_sentence_keys.add(normalized)
                kept_sentences.append(sentence)

            if not kept_sentences and block.body.strip():
                fallback = _most_relevant_sentences(
                    _split_sentences(block.body),
                    query_terms,
                    limit=2,
                )
                kept_sentences = fallback or [block.body.strip()]

            merged_body, block_overlaps = _merge_overlapping_sentences(kept_sentences)
            overlaps_merged += block_overlaps

            if merged_body.strip():
                compressed_blocks.append(
                    ContextBlock(
                        citation_label=block.citation_label,
                        header_line=block.header_line,
                        body=merged_body,
                        score=block.score,
                    )
                )

        compressed_blocks = _enforce_token_budget(
            compressed_blocks,
            query_terms,
            self._max_context_tokens,
        )

        compressed_text = _render_context_blocks(compressed_blocks)
        compressed_tokens = count_tokens(compressed_text)

        return CompressedContext(
            context_text=compressed_text,
            stats=CompressionStats(
                enabled=True,
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                blocks_input=len(blocks),
                blocks_output=len(compressed_blocks),
                duplicate_sentences_removed=duplicate_sentences_removed,
                irrelevant_sentences_removed=irrelevant_sentences_removed,
                overlaps_merged=overlaps_merged,
            ),
        )


def _parse_context_blocks(
    context_text: str,
    built_context: BuiltContext,
) -> list[ContextBlock]:
    raw_blocks = [
        block.strip()
        for block in context_text.split(_BLOCK_SEPARATOR)
        if block.strip()
    ]
    score_by_label = {
        source.citation_label: source.score for source in built_context.sources
    }
    blocks: list[ContextBlock] = []

    for raw_block in raw_blocks:
        lines = raw_block.splitlines()
        if not lines:
            continue

        header_line = lines[0].strip()
        header_match = _HEADER_PATTERN.match(header_line)
        if not header_match:
            blocks.append(
                ContextBlock(
                    citation_label="",
                    header_line=header_line,
                    body="\n".join(lines[1:]).strip(),
                    score=0.0,
                )
            )
            continue

        citation_label = header_match.group(1)
        blocks.append(
            ContextBlock(
                citation_label=citation_label,
                header_line=header_line,
                body="\n".join(lines[1:]).strip(),
                score=score_by_label.get(citation_label, 0.0),
            )
        )

    return blocks


def _compact_boundary_overlaps(text: str) -> tuple[str, int]:
    """Merge clause fragments split across punctuation boundaries."""
    parts = [
        _strip_boundary_punctuation(part.strip())
        for part in re.split(r"(?<=[.!?])\s+", text)
        if part.strip()
    ]
    if len(parts) < 2:
        return text, 0

    compact_parts = [parts[0]]
    merges = 0
    for part in parts[1:]:
        overlap = _suffix_prefix_overlap(compact_parts[-1], part)
        if overlap >= settings.OVERLAP_MERGE_MIN_CHARS:
            compact_parts[-1] = compact_parts[-1] + part[overlap:]
            merges += 1
        else:
            compact_parts.append(part)

    if merges == 0:
        return text, 0
    return ". ".join(compact_parts), merges


def _strip_boundary_punctuation(text: str) -> str:
    return text.strip().rstrip(".!?")


def _split_sentences(text: str) -> list[str]:
    if not text.strip():
        return []

    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    sentences: list[str] = []
    for paragraph in paragraphs:
        parts = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", paragraph)
            if part.strip()
        ]
        if len(parts) <= 1:
            sentences.append(paragraph)
            continue
        sentences.extend(parts)
    return sentences


def _normalize_sentence(sentence: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", sentence.strip().lower())


def _sentence_word_set(sentence: str) -> set[str]:
    return {token for token in _normalize_sentence(sentence).split() if token}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _is_duplicate_sentence(
    normalized: str,
    seen_keys: set[str],
    near_duplicate_threshold: float,
) -> bool:
    if normalized in seen_keys:
        return True

    candidate_words = _sentence_word_set(normalized)
    if not candidate_words:
        return False

    for existing in seen_keys:
        if _jaccard(candidate_words, _sentence_word_set(existing)) >= near_duplicate_threshold:
            return True
    return False


def _is_relevant_sentence(
    normalized: str,
    query_terms: list[str],
    relevance_threshold: float,
) -> bool:
    if not query_terms:
        return True

    hits = sum(1 for term in query_terms if term in normalized)
    return (hits / len(query_terms)) >= relevance_threshold


def _sentence_relevance(sentence: str, query_terms: list[str]) -> float:
    normalized = _normalize_sentence(sentence)
    if not query_terms:
        return 1.0
    hits = sum(1 for term in query_terms if term in normalized)
    return hits / len(query_terms)


def _most_relevant_sentences(
    sentences: list[str],
    query_terms: list[str],
    *,
    limit: int,
) -> list[str]:
    ranked = sorted(
        sentences,
        key=lambda sentence: _sentence_relevance(sentence, query_terms),
        reverse=True,
    )
    return ranked[:limit]


def _suffix_prefix_overlap(left: str, right: str) -> int:
    left = _strip_boundary_punctuation(left)
    right = _strip_boundary_punctuation(right)
    max_size = min(len(left), len(right), 400)
    min_size = settings.OVERLAP_MERGE_MIN_CHARS
    left_lower = left.lower()
    right_lower = right.lower()
    for size in range(max_size, min_size - 1, -1):
        if left_lower[-size:] == right_lower[:size]:
            return size
    return 0


def _merge_overlapping_sentences(sentences: list[str]) -> tuple[str, int]:
    if not sentences:
        return "", 0

    merged: list[str] = [sentences[0]]
    overlaps_merged = 0

    for sentence in sentences[1:]:
        previous = merged[-1]
        overlap = _suffix_prefix_overlap(previous, sentence)
        if overlap >= settings.OVERLAP_MERGE_MIN_CHARS:
            merged[-1] = previous + sentence[overlap:]
            overlaps_merged += 1
        else:
            merged.append(sentence)

    return " ".join(merged), overlaps_merged


def _render_context_blocks(blocks: list[ContextBlock]) -> str:
    rendered: list[str] = []
    for block in blocks:
        if block.header_line:
            rendered.append(f"{block.header_line}\n{block.body}".strip())
        else:
            rendered.append(block.body.strip())
    return _BLOCK_SEPARATOR.join(rendered)


def _enforce_token_budget(
    blocks: list[ContextBlock],
    query_terms: list[str],
    max_tokens: int,
) -> list[ContextBlock]:
    rendered = _render_context_blocks(blocks)
    if count_tokens(rendered) <= max_tokens:
        return blocks

    scored_sentences: list[tuple[float, int, int, str]] = []
    for block_index, block in enumerate(blocks):
        sentences = _split_sentences(block.body)
        for sentence_index, sentence in enumerate(sentences):
            scored_sentences.append(
                (
                    _sentence_relevance(sentence, query_terms),
                    block_index,
                    sentence_index,
                    sentence,
                )
            )

    scored_sentences.sort(key=lambda item: (item[0], item[2]))

    # Drop lowest-relevance sentences until the budget is met.
    removable = scored_sentences[:-1] if scored_sentences else []
    removed: set[tuple[int, int]] = set()

    for _relevance, block_index, sentence_index, _sentence in removable:
        candidate_removed = removed | {(block_index, sentence_index)}
        candidate_blocks = _rebuild_blocks_with_removals(blocks, candidate_removed)
        if not candidate_blocks:
            continue
        if count_tokens(_render_context_blocks(candidate_blocks)) <= max_tokens:
            removed = candidate_removed
            break
        removed = candidate_removed

    return _rebuild_blocks_with_removals(blocks, removed)


def _rebuild_blocks_with_removals(
    blocks: list[ContextBlock],
    removed: set[tuple[int, int]],
) -> list[ContextBlock]:
    rebuilt: list[ContextBlock] = []

    for block_index, block in enumerate(blocks):
        sentences = _split_sentences(block.body)
        kept = [
            sentence
            for sentence_index, sentence in enumerate(sentences)
            if (block_index, sentence_index) not in removed
        ]
        if not kept:
            continue
        merged_body, _ = _merge_overlapping_sentences(kept)
        rebuilt.append(
            ContextBlock(
                citation_label=block.citation_label,
                header_line=block.header_line,
                body=merged_body,
                score=block.score,
            )
        )

    return rebuilt

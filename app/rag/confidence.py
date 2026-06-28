"""Confidence scoring from retrieval quality signals."""

from llama_index.core.schema import NodeWithScore


def compute_confidence_score(nodes: list[NodeWithScore]) -> float:
    """
    Derive a 0–1 confidence score from retrieval similarity scores.

    Uses rank-weighted averaging so higher-ranked chunks influence the score
    more strongly than lower-ranked ones.
    """
    if not nodes:
        return 0.0

    scores = [float(node.score or 0.0) for node in nodes]
    weights = [1.0 / (index + 1) for index in range(len(scores))]
    weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
    total_weight = sum(weights)
    normalized = weighted_sum / total_weight if total_weight else 0.0
    return round(min(max(normalized, 0.0), 1.0), 4)

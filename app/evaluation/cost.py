"""Token-based cost estimation for RAG evaluation runs."""

from dataclasses import dataclass

from app.core.config import settings
from app.utils.tokens import count_tokens

# USD per 1M tokens (approximate OpenAI pricing)
PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


@dataclass(frozen=True)
class CostBreakdown:
    """Estimated cost for a single query evaluation."""

    input_tokens: int
    output_tokens: int
    embedding_tokens: int
    llm_cost_usd: float
    embedding_cost_usd: float

    @property
    def total_cost_usd(self) -> float:
        return self.llm_cost_usd + self.embedding_cost_usd


def estimate_cost(
    *,
    question: str,
    answer: str,
    contexts: list[str],
    llm_model: str | None = None,
    embedding_model: str | None = None,
) -> CostBreakdown:
    """Estimate USD cost from token counts for LLM + embedding calls."""
    llm_model = llm_model or settings.OPENAI_CHAT_MODEL
    embedding_model = embedding_model or settings.OPENAI_EMBEDDING_MODEL

    context_text = "\n".join(contexts)
    input_tokens = count_tokens(f"{question}\n{context_text}", llm_model)
    output_tokens = count_tokens(answer, llm_model)
    embedding_tokens = count_tokens(question, llm_model) + count_tokens(
        context_text, llm_model
    )

    llm_pricing = PRICING.get(llm_model, PRICING["gpt-4o-mini"])
    embed_pricing = PRICING.get(
        embedding_model, PRICING["text-embedding-3-small"]
    )

    llm_cost = (
        input_tokens * llm_pricing["input"] + output_tokens * llm_pricing["output"]
    ) / 1_000_000
    embedding_cost = embedding_tokens * embed_pricing["input"] / 1_000_000

    return CostBreakdown(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        embedding_tokens=embedding_tokens,
        llm_cost_usd=round(llm_cost, 6),
        embedding_cost_usd=round(embedding_cost, 6),
    )

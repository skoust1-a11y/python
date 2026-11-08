"""Tests for Evidence-mode retrieval quality validation."""

from app.utils.evidence_validator import (
    has_sufficient_evidence,
    validate_retrieved_evidence,
)


def _source(
    score: float,
    *,
    text: str,
    label: str = "[Source 1]",
    semantic_score: float | None = None,
) -> dict:
    metadata = {}
    if semantic_score is not None:
        metadata["semantic_score"] = semantic_score
    return {
        "score": score,
        "full_text": text,
        "excerpt": text,
        "citation_label": label,
        "metadata": metadata,
    }


def test_irrelevant_question_rejected():
    """Off-topic questions with weak retrieval should not show evidence."""
    sources = [
        _source(
            0.28,
            text=(
                "This Agreement is entered into between Acme Corp and Beta LLC. "
                "Governing law shall be the State of Delaware."
            ),
            label="[Source 1]",
        ),
        _source(
            0.24,
            text="Payment shall be due within thirty days of invoice date.",
            label="[Source 2]",
        ),
    ]
    assert not has_sufficient_evidence("Who won the FIFA World Cup?", sources)


def test_scenario_question_with_multiple_clauses_accepted():
    """Scenario-style legal questions with strong retrieval should pass."""
    sources = [
        _source(
            0.88,
            text="Late payment shall incur a fee of 2% per month after thirty days.",
            label="[Source 1]",
        ),
        _source(
            0.85,
            text="GST at eighteen percent applies to all taxable services.",
            label="[Source 2]",
        ),
        _source(
            0.82,
            text="The base service fee is four hundred rupees per month.",
            label="[Source 3]",
        ),
    ]
    question = (
        "If payment is 30 days late including GST and late fees, "
        "what clauses apply to the total amount due?"
    )
    assert has_sufficient_evidence(question, sources)


def test_scenario_question_with_moderate_similarity_accepted():
    """Multi-clause scenario questions should pass when chunks cover topics collectively."""
    sources = [
        _source(
            0.55,
            semantic_score=0.32,
            text="Late payment shall incur a fee of 2% per month after thirty days.",
            label="[Source 1]",
        ),
        _source(
            0.52,
            semantic_score=0.30,
            text="GST at eighteen percent applies to all taxable services.",
            label="[Source 2]",
        ),
        _source(
            0.50,
            semantic_score=0.28,
            text="The base service fee is four hundred rupees per month.",
            label="[Source 3]",
        ),
    ]
    question = (
        "If payment is 30 days late including GST and late fees, "
        "what is the total amount due?"
    )
    assert has_sufficient_evidence(question, sources)


def test_gst_inclusive_exclusive_pricing_question_accepted():
    """Hypothetical amounts (400/472) must not block GST pricing questions."""
    sources = [
        _source(
            0.88,
            semantic_score=0.72,
            text="Late payment shall incur a fee of 2% per month after thirty days.",
            label="[Source 1]",
        ),
        _source(
            0.85,
            semantic_score=0.68,
            text="GST at eighteen percent applies to all taxable services.",
            label="[Source 2]",
        ),
        _source(
            0.82,
            semantic_score=0.65,
            text="The base service fee is four hundred rupees per month.",
            label="[Source 3]",
        ),
    ]
    question = (
        "if my goods worth is 400 should i pay 472 or 400 "
        "is it gst inclusive or exclusive"
    )
    assert has_sufficient_evidence(question, sources)


def test_empty_sources_rejected():
    assert not has_sufficient_evidence("What is the termination clause?", [])


def test_low_relevance_rejected_even_with_some_overlap():
    sources = [
        _source(
            0.18,
            text="Termination requires ninety days written notice to the other party.",
            label="[Source 1]",
        ),
    ]
    assert not has_sufficient_evidence(
        "What is the termination notice period?",
        sources,
        relevance_threshold=0.20,
        min_chunk_similarity=0.15,
        query_overlap_threshold=0.10,
    )


def test_inflated_ranking_score_rejected_when_semantic_is_weak():
    """Post-ranking boosts must not bypass evidence validation."""
    sources = [
        _source(
            0.92,
            semantic_score=0.28,
            text="This Agreement is governed by the laws of Delaware.",
            label="[Source 1]",
        ),
    ]
    result = validate_retrieved_evidence(
        "Who is John Smith and what is his role in the company?",
        sources,
    )
    assert not result.sufficient
    assert result.relevance < 0.35


def test_person_name_not_in_documents_rejected():
    sources = [
        _source(
            0.78,
            semantic_score=0.42,
            text=(
                "Each party shall perform its role under this Agreement "
                "in accordance with applicable law."
            ),
            label="[Source 1]",
        ),
    ]
    assert not has_sufficient_evidence("What is Jane Doe responsible for?", sources)


def test_substring_overlap_does_not_count():
    sources = [
        _source(
            0.40,
            semantic_score=0.40,
            text="The contractor does not assign rights without consent.",
            label="[Source 1]",
        ),
    ]
    assert not has_sufficient_evidence("Tell me about John Doe.", sources)


def test_conversational_payment_terms_question_accepted():
    """Natural phrasing like 'tell me about payment terms' must not be rejected."""
    sources = [
        _source(
            0.82,
            semantic_score=0.72,
            text="Payment shall be due within thirty days of invoice date.",
            label="[Source 1]",
        ),
        _source(
            0.78,
            semantic_score=0.68,
            text="All fees are payable in accordance with the payment terms in Schedule A.",
            label="[Source 2]",
        ),
    ]
    assert has_sufficient_evidence("Tell me about the payment terms.", sources)


def test_payment_terms_question_accepted_with_moderate_similarity():
    """On-topic keyword overlap should allow moderate semantic scores."""
    sources = [
        _source(
            0.55,
            semantic_score=0.30,
            text="Payment terms require settlement within thirty days of invoice.",
            label="[Source 1]",
        ),
    ]
    assert has_sufficient_evidence("What are the payment terms?", sources)


def test_payment_delayed_scenario_accepted():
    """'What happens if payment is delayed?' is a common scenario regression case."""
    sources = [
        _source(
            0.55,
            semantic_score=0.32,
            text="Payment shall be due within thirty days of invoice date.",
            label="[Source 1]",
        ),
        _source(
            0.52,
            semantic_score=0.30,
            text="Late payment shall incur a fee of 1.5% per month after thirty days.",
            label="[Source 2]",
        ),
    ]
    assert has_sufficient_evidence("What happens if payment is delayed?", sources)


def test_employee_resign_without_notice_scenario_accepted():
    sources = [
        _source(
            0.60,
            semantic_score=0.38,
            text="Either party may terminate employment with thirty days written notice.",
            label="[Source 1]",
        ),
        _source(
            0.58,
            semantic_score=0.35,
            text="Resignation without notice forfeits accrued benefits under this policy.",
            label="[Source 2]",
        ),
    ]
    question = "If an employee resigns without notice, what are the consequences?"
    assert has_sufficient_evidence(question, sources)


def test_tenant_terminate_scenario_accepted():
    sources = [
        _source(
            0.65,
            semantic_score=0.40,
            text="The tenant may terminate this lease upon thirty days written notice.",
            label="[Source 1]",
        ),
    ]
    question = "Can a tenant terminate the agreement under these circumstances?"
    assert has_sufficient_evidence(question, sources)


def test_scenario_terms_spread_across_chunks_use_collective_overlap():
    """No single chunk may contain every query term in multi-clause scenarios."""
    sources = [
        _source(
            0.50,
            semantic_score=0.30,
            text="GST at eighteen percent applies to all taxable services.",
            label="[Source 1]",
        ),
        _source(
            0.48,
            semantic_score=0.28,
            text="Resignation without notice requires forfeiture of the service fee deposit.",
            label="[Source 2]",
        ),
    ]
    question = "If an employee resigns without notice, does GST apply to the service fee?"
    assert has_sufficient_evidence(question, sources)


def test_is_directly_relevant_payment_terms():
    from app.utils.evidence_validator import is_directly_relevant

    text = "Payment shall be due within thirty days of invoice date."
    assert is_directly_relevant("Tell me about the payment terms.", text)


def test_is_directly_relevant_rejects_indirect_gst_clause():
    from app.utils.evidence_validator import is_directly_relevant

    text = "GST shall be applied at the prevailing rate on all taxable supplies."
    assert not is_directly_relevant("Tell me about the payment terms.", text)


def test_filter_direct_sources_keeps_gst_chunks_for_pricing_question():
    from app.utils.evidence_validator import filter_direct_sources

    sources = [
        _source(0.4, text="Late payment shall incur a fee of 2% per month.", label="[Source 1]"),
        _source(0.85, text="GST at eighteen percent applies to all taxable services.", label="[Source 2]"),
        _source(0.82, text="The base service fee is four hundred rupees per month.", label="[Source 3]"),
    ]
    question = (
        "if my goods worth is 400 should i pay 472 or 400 "
        "is it gst inclusive or exclusive"
    )
    direct = filter_direct_sources(question, sources)
    labels = {source["citation_label"] for source in direct}
    assert "[Source 2]" in labels
    assert "[Source 3]" in labels

    sources = [
        _source(
            0.80,
            semantic_score=0.72,
            text="Payment shall be due within thirty days of invoice date.",
            label="[Source 1]",
        ),
        _source(
            0.75,
            semantic_score=0.68,
            text="GST shall be applied at the prevailing rate on all taxable supplies.",
            label="[Source 2]",
        ),
    ]
    direct = filter_direct_sources("Tell me about the payment terms.", sources)
    assert len(direct) == 1
    assert "Payment shall be due" in direct[0]["full_text"]


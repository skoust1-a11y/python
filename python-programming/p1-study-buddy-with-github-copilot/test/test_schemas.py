from app.schemas import ConceptRequest, ExplanationResponse


def test_concept_request_accepts_concept():
    payload = ConceptRequest(concept="RAG")
    assert payload.concept == "RAG"


def test_explanation_response_fields():
    payload = ExplanationResponse(
        concept="RAG",
        explanation="RAG combines retrieval and generation.",
        model="gemini-test-model",
    )
    assert payload.model == "gemini-test-model"
    assert "retrieval" in payload.explanation

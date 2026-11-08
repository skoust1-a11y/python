"""Human handoff escalation API endpoints."""

import logging

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_handoff_service
from app.models.schemas import HandoffRequest, HandoffResponse
from app.services.handoff_service import HandoffService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["handoff"])


@router.post(
    "/handoff",
    response_model=HandoffResponse,
    summary="Escalate query to human reviewer",
    description=(
        "Evaluate a query interaction for human handoff. Escalates when confidence "
        "is below 0.70, no supporting citations are present, or the user requests "
        "high-risk legal advice. Persists summary, conversation history, retrieved "
        "documents, and sources for reviewer follow-up."
    ),
    responses={
        200: {"description": "No escalation required"},
        201: {"description": "Escalation created for human review"},
    },
)
async def create_handoff(
    body: HandoffRequest,
    response: Response,
    handoff_service: HandoffService = Depends(get_handoff_service),
) -> HandoffResponse:
    logger.info(
        "Handoff request: question_length=%d confidence=%.4f",
        len(body.question),
        body.confidence_score,
    )
    result = await handoff_service.process_handoff(body)
    response.status_code = 201 if result.escalated else 200
    return result

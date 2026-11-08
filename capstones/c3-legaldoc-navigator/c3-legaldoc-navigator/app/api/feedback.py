"""User feedback API endpoints."""

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_feedback_service
from app.models.schemas import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=201,
    summary="Submit query feedback",
    description=(
        "Record user satisfaction ratings and optional comments on query responses. "
        "Used for quality monitoring and evaluation."
    ),
)
async def submit_feedback(
    body: FeedbackRequest,
    feedback_service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackResponse:
    logger.info("Feedback submission: rating=%d", body.rating)
    return await feedback_service.submit_feedback(body)

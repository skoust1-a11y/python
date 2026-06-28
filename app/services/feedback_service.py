"""User feedback collection for query quality monitoring."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import Feedback
from app.models.schemas import FeedbackRequest, FeedbackResponse

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def submit_feedback(self, payload: FeedbackRequest) -> FeedbackResponse:
        """Persist user feedback on a query interaction."""
        record = Feedback(
            rating=payload.rating,
            comment=payload.comment,
            query_text=payload.query_text,
            document_id=payload.document_id,
            session_id=payload.session_id,
        )
        self._session.add(record)
        await self._session.flush()

        logger.info(
            "Feedback recorded: id=%s rating=%d document_id=%s",
            record.id,
            record.rating,
            payload.document_id,
        )

        return FeedbackResponse(
            id=record.id,
            rating=record.rating,
            comment=record.comment,
            created_at=record.created_at,
        )

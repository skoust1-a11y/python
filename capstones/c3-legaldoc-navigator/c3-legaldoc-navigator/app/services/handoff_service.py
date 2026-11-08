"""Human handoff escalation business logic."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.handoff.evaluator import evaluate_escalation_triggers
from app.handoff.summary import generate_handoff_summary
from app.models.orm import Document, HandoffEscalation
from app.models.schemas import (
    ConversationTurn,
    HandoffRequest,
    HandoffResponse,
    RetrievedDocumentSummary,
    SourceCitation,
)

logger = logging.getLogger(__name__)


class HandoffService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def process_handoff(self, payload: HandoffRequest) -> HandoffResponse:
        """Evaluate escalation triggers and persist a handoff record when warranted."""
        source_dicts = [source.model_dump(mode="json") for source in payload.sources]
        history_dicts = [turn.model_dump(mode="json") for turn in payload.conversation_history]

        evaluation = evaluate_escalation_triggers(
            question=payload.question,
            answer=payload.answer or "",
            confidence_score=payload.confidence_score,
            sources=source_dicts,
        )

        if not evaluation.should_escalate:
            return HandoffResponse(
                escalated=False,
                reasons=evaluation.reasons,
            )

        retrieved_documents = await self._resolve_retrieved_documents(
            payload,
            source_dicts,
        )
        retrieved_doc_dicts = [doc.model_dump(mode="json") for doc in retrieved_documents]

        summary = generate_handoff_summary(
            question=payload.question,
            answer=payload.answer,
            confidence_score=payload.confidence_score,
            escalation_reasons=evaluation.reasons,
            sources=source_dicts,
            conversation_history=history_dicts,
            retrieved_documents=retrieved_doc_dicts,
        )

        record = HandoffEscalation(
            session_id=payload.session_id,
            user_id=payload.user_id,
            document_id=payload.document_id,
            query_text=payload.question,
            answer=payload.answer,
            summary=summary,
            conversation_history=history_dicts,
            retrieved_documents=retrieved_doc_dicts,
            sources=source_dicts,
            confidence_score=payload.confidence_score,
            escalation_reasons=evaluation.reasons,
            status="pending",
        )
        self._session.add(record)
        await self._session.flush()

        logger.info(
            "Handoff escalation created: id=%s reasons=%s confidence=%.4f",
            record.id,
            evaluation.reasons,
            payload.confidence_score,
        )

        return HandoffResponse(
            escalated=True,
            escalation_id=record.id,
            reasons=evaluation.reasons,
            summary=summary,
            conversation_history=payload.conversation_history,
            retrieved_documents=retrieved_documents,
            sources=payload.sources,
            status=record.status,
            created_at=record.created_at,
        )

    async def _resolve_retrieved_documents(
        self,
        payload: HandoffRequest,
        sources: list[dict],
    ) -> list[RetrievedDocumentSummary]:
        document_ids: set[UUID] = set()
        if payload.document_id:
            document_ids.add(payload.document_id)

        for source in sources:
            doc_id = source.get("document_id")
            if doc_id:
                try:
                    document_ids.add(UUID(str(doc_id)))
                except (TypeError, ValueError):
                    continue

        if not document_ids:
            return []

        result = await self._session.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        documents = result.scalars().all()

        return [
            RetrievedDocumentSummary(
                id=doc.id,
                filename=doc.filename,
                title=doc.title,
                file_type=doc.file_type,
                status=doc.status,
                contract_id=doc.contract_id,
                document_subtype=doc.document_subtype,
            )
            for doc in documents
        ]

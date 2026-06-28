"""Document management business logic."""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import DocumentNotFoundError, FileTooLargeError, FileValidationError, IngestionError
from app.ingestion.pipeline import IngestionPipeline
from app.models.orm import Document
from app.models.schemas import DocumentDetailResponse, DocumentListResponse, DocumentSummary, DocumentUploadResponse
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import ChunkToStore, VectorStoreService
from app.utils.file_utils import compute_file_hash, ensure_upload_dir, validate_file_extension

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        pipeline: IngestionPipeline | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStoreService | None = None,
    ) -> None:
        self._session = session
        self._pipeline = pipeline or IngestionPipeline()
        self._embedding_service = embedding_service or EmbeddingService()
        self._vector_store = vector_store or VectorStoreService(
            session, embedding_service=self._embedding_service
        )

    async def upload_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Save, parse, chunk, embed, and persist a legal document."""
        if not file.filename:
            raise FileValidationError("Uploaded file must include a filename.")

        try:
            validate_file_extension(file.filename)
        except ValueError as exc:
            raise FileValidationError(str(exc)) from exc

        content = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise FileTooLargeError(settings.MAX_UPLOAD_SIZE_MB)

        upload_dir = ensure_upload_dir()
        stored_name = f"{uuid.uuid4().hex}_{file.filename}"
        dest_path = upload_dir / stored_name

        await asyncio.to_thread(dest_path.write_bytes, content)
        content_hash = await asyncio.to_thread(compute_file_hash, dest_path)

        file_type = Path(file.filename).suffix.lstrip(".").lower()
        document = Document(
            filename=file.filename,
            file_type=file_type,
            storage_path=str(dest_path),
            status="processing",
            content_hash=content_hash,
            file_size_bytes=len(content),
        )
        self._session.add(document)
        await self._session.flush()

        logger.info("Document upload started: id=%s filename=%s", document.id, file.filename)

        try:
            parsed, chunks, _nodes = await self._pipeline.ingest(dest_path)
            chunk_payloads = [
                ChunkToStore(
                    chunk_text=text,
                    chunk_index=index,
                    metadata=self._pipeline.build_node_metadata(parsed),
                )
                for index, text in enumerate(chunks)
            ]
            await self._vector_store.embed_and_store(document.id, chunk_payloads)

            document.title = parsed.title
            document.status = "indexed"
            document.chunk_count = len(chunks)
            document.doc_metadata = self._pipeline.build_node_metadata(parsed)
            await self._session.flush()

            logger.info(
                "Document indexed: id=%s chunks=%d",
                document.id,
                len(chunks),
            )
        except Exception as exc:
            document.status = "failed"
            await self._session.flush()
            logger.exception("Document ingestion failed: id=%s", document.id)
            raise IngestionError(f"Failed to ingest document: {exc}") from exc

        return DocumentUploadResponse(
            id=document.id,
            filename=document.filename,
            status=document.status,
            chunk_count=document.chunk_count or 0,
            title=document.title,
            file_type=document.file_type,
            created_at=document.created_at,
        )

    async def list_documents(self, *, skip: int = 0, limit: int = 50) -> DocumentListResponse:
        """Return a paginated list of uploaded documents."""
        limit = min(max(limit, 1), 100)
        skip = max(skip, 0)

        total_result = await self._session.execute(select(func.count()).select_from(Document))
        total = int(total_result.scalar_one())

        result = await self._session.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        documents = result.scalars().all()

        return DocumentListResponse(
            items=[DocumentSummary.model_validate(doc) for doc in documents],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_document(self, document_id: uuid.UUID) -> DocumentDetailResponse:
        """Fetch a single document by primary key."""
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(str(document_id))

        return DocumentDetailResponse.model_validate(document)

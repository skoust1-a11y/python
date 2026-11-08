"""Document object storage backends for uploaded files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.utils.file_utils import ensure_upload_dir

_CONTENT_TYPES_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


@dataclass(frozen=True)
class StoredObject:
    storage_path: str
    object_key: str


class DocumentStorageService:
    """Persist original uploaded documents to local or managed object storage."""

    def __init__(self, *, backend: str | None = None) -> None:
        self._backend = (backend or settings.STORAGE_BACKEND).lower()

    async def upload_document(
        self,
        *,
        object_name: str,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        if self._backend == "supabase":
            return await self._upload_to_supabase(
                object_name=object_name,
                content=content,
                content_type=content_type,
            )
        if self._backend == "s3":
            return await self._upload_to_s3(
                object_name=object_name,
                content=content,
                content_type=content_type,
            )
        if self._backend == "local":
            return await self._upload_to_local(object_name=object_name, content=content)
        raise ValueError(f"Unsupported storage backend: {self._backend}")

    async def _upload_to_local(self, *, object_name: str, content: bytes) -> StoredObject:
        upload_dir = ensure_upload_dir()
        dest_path = upload_dir / object_name
        await asyncio.to_thread(dest_path.write_bytes, content)
        return StoredObject(storage_path=str(dest_path), object_key=object_name)

    async def _upload_to_supabase(
        self,
        *,
        object_name: str,
        content: bytes,
        content_type: str | None,
    ) -> StoredObject:
        object_key = self._build_object_key(object_name)
        encoded_key = "/".join(quote(part, safe="") for part in object_key.split("/"))
        bucket = quote(settings.SUPABASE_STORAGE_BUCKET, safe="")
        url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{bucket}/{encoded_key}"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": self._content_type_for_upload(object_name, content_type),
            "x-upsert": "false",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=content)
        if response.status_code >= 400:
            raise RuntimeError(
                "Supabase Storage upload failed "
                f"({response.status_code}): {response.text[:500]}"
            )

        storage_path = f"supabase://{settings.SUPABASE_STORAGE_BUCKET}/{object_key}"
        return StoredObject(storage_path=storage_path, object_key=object_key)

    async def _upload_to_s3(
        self,
        *,
        object_name: str,
        content: bytes,
        content_type: str | None,
    ) -> StoredObject:
        object_key = self._build_s3_object_key(object_name)
        await asyncio.to_thread(
            self._put_s3_object,
            object_key=object_key,
            content=content,
            content_type=self._content_type_for_upload(object_name, content_type),
        )
        storage_path = f"s3://{settings.S3_BUCKET}/{object_key}"
        return StoredObject(storage_path=storage_path, object_key=object_key)

    @staticmethod
    def _put_s3_object(*, object_key: str, content: bytes, content_type: str) -> None:
        import boto3

        client_kwargs: dict[str, str] = {
            "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
            "region_name": settings.S3_REGION,
        }
        if settings.S3_ENDPOINT_URL.strip():
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL.strip()

        client = boto3.client("s3", **client_kwargs)
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Body=content,
            ContentType=content_type,
        )

    @staticmethod
    def _build_object_key(object_name: str) -> str:
        prefix = settings.SUPABASE_STORAGE_PATH_PREFIX.strip("/")
        name = Path(object_name).name
        return f"{prefix}/{name}" if prefix else name

    @staticmethod
    def _build_s3_object_key(object_name: str) -> str:
        prefix = settings.S3_PATH_PREFIX.strip("/")
        name = Path(object_name).name
        return f"{prefix}/{name}" if prefix else name

    @staticmethod
    def _content_type_for_upload(object_name: str, content_type: str | None) -> str:
        if content_type and content_type != "application/octet-stream":
            return content_type
        suffix = Path(object_name).suffix.lower()
        return _CONTENT_TYPES_BY_EXTENSION.get(suffix, "application/octet-stream")

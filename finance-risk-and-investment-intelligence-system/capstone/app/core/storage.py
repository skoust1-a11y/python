"""Corpus storage Protocol (ADR-018). Local now; S3 later."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from app.core.config import get_settings
from app.core.db import CAPSTONE_ROOT


@runtime_checkable
class CorpusStore(Protocol):
    def root(self) -> Path: ...
    def read_bytes(self, relative: str) -> bytes: ...
    def write_bytes(self, relative: str, data: bytes) -> Path: ...
    def exists(self, relative: str) -> bool: ...


class LocalCorpusStore:
    def __init__(self, base: Optional[Path] = None):
        if base is None:
            raw = Path(get_settings().corpus_local_path)
            base = raw if raw.is_absolute() else CAPSTONE_ROOT / raw
        self._base = base

    def root(self) -> Path:
        return self._base

    def read_bytes(self, relative: str) -> bytes:
        return (self._base / relative).read_bytes()

    def write_bytes(self, relative: str, data: bytes) -> Path:
        path = self._base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def exists(self, relative: str) -> bool:
        return (self._base / relative).is_file()


class S3CorpusStore:
    """Stub for cloud object storage - not used in the capstone local bar."""

    def root(self) -> Path:
        raise NotImplementedError("S3CorpusStore is a cloud stub")

    def read_bytes(self, relative: str) -> bytes:
        raise NotImplementedError("S3CorpusStore is a cloud stub")

    def write_bytes(self, relative: str, data: bytes) -> Path:
        raise NotImplementedError("S3CorpusStore is a cloud stub")

    def exists(self, relative: str) -> bool:
        raise NotImplementedError("S3CorpusStore is a cloud stub")


def get_corpus_store() -> CorpusStore:
    return LocalCorpusStore()

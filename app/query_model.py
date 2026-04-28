"""SQLAlchemy models for storing user study queries and LLM responses."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for ORM models."""


class QueryLog(Base):
    """Database table capturing each tutoring query and generated answer."""

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept: Mapped[str] = mapped_column(String(255), index=True)
    query_text: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

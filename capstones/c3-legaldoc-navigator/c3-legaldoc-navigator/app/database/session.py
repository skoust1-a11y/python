"""SQLAlchemy async engine and session factory."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import database_target_label, settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async_session_factory = AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def verify_database_connection() -> None:
    """Fail fast when PostgreSQL credentials or connectivity are invalid."""
    logger.info("PostgreSQL runtime target: %s", database_target_label(settings.DATABASE_URL))
    if settings.DATABASE_SYNC_URL != settings.DATABASE_URL:
        logger.info(
            "PostgreSQL migration target: %s",
            database_target_label(settings.DATABASE_SYNC_URL, source="DATABASE_SYNC_URL"),
        )

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

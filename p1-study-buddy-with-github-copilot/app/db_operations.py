"""Database setup and write operations for LLM query persistence."""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from .query_model import Base, QueryLog

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./llm_queries.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create required database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def insert_query_record(
    concept: str,
    query_text: str,
    explanation: str | None,
    model: str | None,
) -> int | None:
    """Insert one query log row and return the new row ID when successful."""
    session = SessionLocal()
    try:
        entry = QueryLog(
            concept=concept,
            query_text=query_text,
            explanation=explanation,
            model=model,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry.id
    except SQLAlchemyError as exc:
        session.rollback()
        logger.warning("Could not persist query record: %s", exc)
        return None
    finally:
        session.close()

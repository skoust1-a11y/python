from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

CAPSTONE_ROOT = Path(__file__).resolve().parents[2]


def resolve_db_url(url: str) -> str:
    """Pin relative sqlite files to capstone/ so cwd does not matter."""
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    if not url.startswith("sqlite:///") or url.startswith("sqlite:///:memory:"):
        return url
    path = url[len("sqlite:///") :]
    if path and not os.path.isabs(path):
        path = str(CAPSTONE_ROOT / path)
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    return "sqlite:///" + path


def _sqlite_path(url: str) -> str:
    if not url.startswith("sqlite:///") or url.startswith("sqlite:///:memory:"):
        return ""
    return url.split("sqlite:///", 1)[-1]


def _engine(url: str):
    url = resolve_db_url(url)
    if url.startswith("sqlite"):
        path = _sqlite_path(url)
        if path and path != ":memory:":
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
        engine = create_engine(
            url,
            future=True,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _fk(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine
    return create_engine(url, future=True, pool_pre_ping=True)


settings = get_settings()
auth_engine = _engine(settings.auth_database_url)
finance_engine = _engine(settings.database_url)
stock_engine = _engine(settings.stock_database_url)
AuthSessionLocal = sessionmaker(bind=auth_engine, autoflush=False, autocommit=False, future=True)
FinanceSessionLocal = sessionmaker(bind=finance_engine, autoflush=False, autocommit=False, future=True)
StockSessionLocal = sessionmaker(bind=stock_engine, autoflush=False, autocommit=False, future=True)


def get_auth_db() -> Generator[Session, None, None]:
    session = AuthSessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_finance_db() -> Generator[Session, None, None]:
    session = FinanceSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _ensure_holding_columns() -> None:
    statements = (
        "ALTER TABLE portfolio_holdings ADD COLUMN IF NOT EXISTS buy_price NUMERIC",
        "ALTER TABLE portfolio_holdings ADD COLUMN IF NOT EXISTS buy_date DATE",
    )
    with finance_engine.begin() as conn:
        if finance_engine.dialect.name == "sqlite":
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(portfolio_holdings)"))}
            if "buy_price" not in cols:
                conn.execute(text("ALTER TABLE portfolio_holdings ADD COLUMN buy_price NUMERIC"))
            if "buy_date" not in cols:
                conn.execute(text("ALTER TABLE portfolio_holdings ADD COLUMN buy_date DATE"))
            return
        for sql in statements:
            conn.execute(text(sql))


def _ensure_user_document_columns() -> None:
    with finance_engine.begin() as conn:
        if finance_engine.dialect.name == "sqlite":
            tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
            if "user_documents" not in tables:
                return
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(user_documents)"))}
            if "use_case" not in cols:
                conn.execute(text("ALTER TABLE user_documents ADD COLUMN use_case VARCHAR DEFAULT 'all'"))
            if "profile_id" not in cols:
                conn.execute(text("ALTER TABLE user_documents ADD COLUMN profile_id VARCHAR DEFAULT 'default'"))
            return
        exists = conn.execute(text("SELECT to_regclass('public.user_documents')")).scalar()
        if not exists:
            return
        conn.execute(text("ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS use_case VARCHAR DEFAULT 'all'"))
        conn.execute(text("ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS profile_id VARCHAR DEFAULT 'default'"))


def _ensure_stock_document_columns() -> None:
    with stock_engine.begin() as conn:
        if stock_engine.dialect.name == "sqlite":
            tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
            if "stock_documents" not in tables:
                return
            cols = {row[1] for row in conn.execute(text("PRAGMA table_info(stock_documents)"))}
            if "profile_id" not in cols:
                conn.execute(text("ALTER TABLE stock_documents ADD COLUMN profile_id VARCHAR DEFAULT 'default'"))
            if "kind" not in cols:
                conn.execute(text("ALTER TABLE stock_documents ADD COLUMN kind VARCHAR DEFAULT 'ar'"))
            if "body" not in cols:
                conn.execute(text("ALTER TABLE stock_documents ADD COLUMN body TEXT"))
            return
        exists = conn.execute(text("SELECT to_regclass('public.stock_documents')")).scalar()
        if not exists:
            return
        conn.execute(text("ALTER TABLE stock_documents ADD COLUMN IF NOT EXISTS profile_id VARCHAR DEFAULT 'default'"))
        conn.execute(text("ALTER TABLE stock_documents ADD COLUMN IF NOT EXISTS kind VARCHAR DEFAULT 'ar'"))
        conn.execute(text("ALTER TABLE stock_documents ADD COLUMN IF NOT EXISTS body TEXT"))


def _add_col(conn, dialect: str, table: str, column: str, spec: str) -> None:
    if dialect == "sqlite":
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        if table not in tables:
            return
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info({})".format(table)))}
        if column not in cols:
            conn.execute(text("ALTER TABLE {} ADD COLUMN {}".format(table, spec)))
        return
    exists = conn.execute(text("SELECT to_regclass('public.{}')".format(table))).scalar()
    if not exists:
        return
    conn.execute(text("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {}".format(table, spec)))


def _ensure_auth_columns() -> None:
    dialect = auth_engine.dialect.name
    with auth_engine.begin() as conn:
        _add_col(conn, dialect, "turns", "profile_id", "profile_id VARCHAR DEFAULT 'default'")
        _add_col(conn, dialect, "saved_screens", "profile_id", "profile_id VARCHAR DEFAULT 'default'")
        _add_col(conn, dialect, "sessions", "title", "title VARCHAR")


def _ensure_embedding_columns() -> None:
    for engine, table in ((finance_engine, "policy_chunks"), (stock_engine, "stock_chunks")):
        with engine.begin() as conn:
            _add_col(conn, engine.dialect.name, table, "embedding", "embedding TEXT")
        if engine.dialect.name != "postgresql":
            continue
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                _add_col(
                    conn,
                    "postgresql",
                    table,
                    "embedding_vec",
                    "embedding_vec vector GENERATED ALWAYS AS (CAST(embedding AS vector)) STORED",
                )
        except SQLAlchemyError:
            pass  # no pgvector: retrieval falls back to Python cosine


def init_schema() -> None:
    from app import models as _models  # noqa: F401 — register UserDocument on FinanceBase.metadata
    from app.models import AuthBase, FinanceBase, StockBase

    AuthBase.metadata.create_all(bind=auth_engine)
    FinanceBase.metadata.create_all(bind=finance_engine)
    StockBase.metadata.create_all(bind=stock_engine)
    _ensure_holding_columns()
    _ensure_user_document_columns()
    _ensure_stock_document_columns()
    _ensure_auth_columns()
    _ensure_embedding_columns()


def drop_schema() -> None:
    from app.models import AuthBase, FinanceBase, StockBase

    AuthBase.metadata.drop_all(bind=auth_engine)
    FinanceBase.metadata.drop_all(bind=finance_engine)
    StockBase.metadata.drop_all(bind=stock_engine)


def reset_engines(auth_url: str, finance_url: str, stock_url: Optional[str] = None) -> None:
    """Test helper: rebuild session factories against isolated databases."""
    global auth_engine, finance_engine, stock_engine, AuthSessionLocal, FinanceSessionLocal, StockSessionLocal
    auth_engine = _engine(auth_url)
    finance_engine = _engine(finance_url)
    stock_engine = _engine(stock_url or get_settings().stock_database_url)
    AuthSessionLocal = sessionmaker(bind=auth_engine, autoflush=False, autocommit=False, future=True)
    FinanceSessionLocal = sessionmaker(bind=finance_engine, autoflush=False, autocommit=False, future=True)
    StockSessionLocal = sessionmaker(bind=stock_engine, autoflush=False, autocommit=False, future=True)

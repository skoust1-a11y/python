import logging
import os

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    SQLALCHEMY_AVAILABLE = True
except ImportError as e:
    SQLALCHEMY_AVAILABLE = False
    SQLALCHEMY_IMPORT_ERROR = e

if not SQLALCHEMY_AVAILABLE:
    raise ImportError(
        "SQLAlchemy is required for ORM database handling. "
        "Install it with: pip install SQLAlchemy==2.0.34"
    )

# Shared declarative base — imported by models
Base = declarative_base()


class DatabaseConfig:
    def __init__(self):
        self._database_url = None
        self._engine = None
        self._sessionmaker = None
        self._initialized = False

    def _build_database_url(self) -> str:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url

        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME")

        if not all([user, password, dbname]):
            raise ValueError(
                "Postgres configuration is missing. "
                "Set DATABASE_URL or DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME in .env."
            )

        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"

    def get_database_url(self) -> str:
        if self._database_url is None:
            self._database_url = self._build_database_url()
        return self._database_url

    def get_engine(self):
        if self._engine is None:
            self._engine = create_engine(
                self.get_database_url(), future=True, pool_pre_ping=True
            )
        return self._engine

    def get_sessionmaker(self):
        if self._sessionmaker is None:
            self._sessionmaker = sessionmaker(
                bind=self.get_engine(),
                autoflush=False,
                expire_on_commit=False,
                future=True,
            )
        return self._sessionmaker

    def initialize_database(self):
        if self._initialized:
            return

        db_logger = logging.getLogger(__name__)
        db_logger.info("Initializing database schema")
        try:
            Base.metadata.create_all(self.get_engine())
            db_logger.info("Database schema initialized successfully")
            self._initialized = True
        except Exception as e:
            db_logger.error(f"Failed to initialize database schema: {e}")
            raise


# Global database configuration instance
db_config = DatabaseConfig()

# Expose a session factory for ORM usage
SessionLocal = db_config.get_sessionmaker()


def initialize_database():
    """Initialize the database schema."""
    db_config.initialize_database()

"""
SUBSENSE — Database Session Management (Phase 4)

Provides:
  engine          SQLAlchemy sync engine (psycopg2)
  SessionLocal    Session factory for use across the app
  get_db()        FastAPI dependency — yields a session per request

Why sync (not async)?
---------------------
Python 3.14 does not yet have stable asyncpg wheels. To avoid build issues
on the target machine, we use psycopg2-binary (sync driver) throughout.
FastAPI automatically runs sync route handlers in a threadpool, so this
does NOT block the event loop.

When asyncpg wheels land for Python 3.14, upgrade to:
  create_async_engine(...) + AsyncSession
with no changes to the repository layer interface.
"""

from collections.abc import Generator
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base

logger = structlog.get_logger(__name__)

# ── Engine ───────────────────────────────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,      # Recycles stale connections automatically
    echo=settings.database_echo,
)

# ── Session factory ──────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Avoid lazy-load errors after commit
)


# ── FastAPI dependency ───────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session per HTTP request, close it when done.

    Usage in a route:
        def my_route(db: DbSession):
            results = db.query(SensorReading).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Convenience type alias for route signatures
DbSession = Annotated[Session, Depends(get_db)]


# ── Startup helpers ──────────────────────────────────────────────────────────

def init_db() -> None:
    """
    Create all tables if they don't already exist.
    Called at FastAPI startup.

    In production, Alembic handles migrations. This function is a
    safe fallback for development / first run.
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("db_tables_ready")
    except Exception as exc:
        logger.error("db_init_failed", error=str(exc))
        raise


def check_db_connection() -> bool:
    """Return True if the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

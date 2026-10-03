"""
Database session management for the AI Incident Response Platform.

Provides sync and async session factories plus a health-check helper.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "incident_platform")
    user = os.getenv("POSTGRES_USER", "platform")
    password = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# Global engine — created lazily on first import in a running app.
# Tests and CLI tools can override by calling init_engine().
_engine = None
_session_factory = None


def init_engine(url: str | None = None):
    """Initialize the global SQLAlchemy engine and session factory."""
    global _engine, _session_factory
    _engine = create_engine(
        url or get_database_url(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = sessionmaker(bind=_engine)


def get_engine():
    """Return the global engine, initializing if needed."""
    if _engine is None:
        init_engine()
    return _engine


def get_session() -> Session:
    """Create a new database session."""
    if _session_factory is None:
        init_engine()
    return _session_factory()


def check_database_health() -> dict:
    """
    Verify database connectivity.

    Returns a dict with 'connected' bool and optional 'error' message.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.scalar()
        return {"connected": True}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}

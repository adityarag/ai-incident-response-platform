"""
API Gateway — Main FastAPI Application

The API Gateway is the entry point for client requests.
It provides health/readiness endpoints and will eventually
route requests to downstream microservices (Order, Payment).
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import create_engine, text

# ── Logging ────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("api-gateway")

# ── Database helper ────────────────────────────────────────


def _get_database_url() -> str:
    """Build PostgreSQL URL from environment."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "incident_platform")
    user = os.getenv("POSTGRES_USER", "platform")
    pw = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


def _check_db() -> dict:
    """Quick database connectivity check."""
    try:
        engine = create_engine(_get_database_url(), pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return {"status": "connected"}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return {"status": "disconnected", "error": str(exc)}


# ── Lifespan ───────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown."""
    logger.info("API Gateway starting up")
    db_health = _check_db()
    logger.info("Database check: %s", db_health["status"])
    yield
    logger.info("API Gateway shutting down")


# ── FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title="AI Incident Response Platform — API Gateway",
    description=(
        "Entry point for the cloud-native application. "
        "Routes requests to downstream services and provides "
        "health/readiness endpoints."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ── Health Endpoints ───────────────────────────────────────


@app.get("/health", tags=["health"])
def health():
    """
    Liveness probe.

    Returns basic service health and database connectivity status.
    """
    db = _check_db()
    overall = "healthy" if db["status"] == "connected" else "degraded"
    return {
        "status": overall,
        "service": "api-gateway",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db,
        },
    }


@app.get("/ready", tags=["health"])
def readiness():
    """
    Readiness probe.

    Returns whether the service is ready to accept traffic.
    """
    db = _check_db()
    ready = db["status"] == "connected"
    return {
        "ready": ready,
        "service": "api-gateway",
    }


@app.get("/", tags=["root"])
def root():
    """Root endpoint — API information."""
    return {
        "service": "api-gateway",
        "version": "0.1.0",
        "description": "AI Incident Response Platform — API Gateway",
        "docs": "/docs",
    }

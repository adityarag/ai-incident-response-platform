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

try:
    from observability.telemetry import setup_service_logger, attach_observability, setup_opentelemetry
    logger = setup_service_logger("api-gateway")
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger("api-gateway")
    attach_observability = None
    setup_opentelemetry = None

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
    """Quick database connectivity check with fault-injection simulation check."""
    try:
        from fault_injection.manager import fault_manager
        if fault_manager.is_db_failure_simulated("api-gateway"):
            return {"status": "disconnected", "error": "Simulated database connection failure / pool exhaustion"}
    except ImportError:
        pass

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

try:
    from fault_injection.middleware import attach_fault_injection
    attach_fault_injection(app, "api-gateway")
except ImportError:
    pass

if attach_observability:
    attach_observability(app, "api-gateway")
if setup_opentelemetry:
    setup_opentelemetry("api-gateway", app)


# ── Middleware ─────────────────────────────────────────────

import uuid
from fastapi import Header, HTTPException, Request, Response, status
import httpx
from app.config import get_settings

settings = get_settings()


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


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


# ── Reverse Proxy / Routing Endpoints ──────────────────────


@app.post("/api/v1/orders", tags=["orders"], status_code=status.HTTP_201_CREATED)
async def create_order_proxy(
    request: Request,
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    """Proxy order creation to Order Service."""
    url = f"{settings.order_service_url.rstrip('/')}/orders"
    body = await request.json()
    headers = {"X-Correlation-ID": x_correlation_id or str(uuid.uuid4())}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/json",
            headers={"X-Correlation-ID": headers["X-Correlation-ID"]},
        )
    except httpx.RequestError as exc:
        logger.error(f"Failed to proxy request to order service: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Order service unavailable: {str(exc)}",
        )


@app.get("/api/v1/orders/{order_id}", tags=["orders"])
async def get_order_proxy(
    order_id: str,
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    """Proxy order lookup to Order Service."""
    url = f"{settings.order_service_url.rstrip('/')}/orders/{order_id}"
    headers = {"X-Correlation-ID": x_correlation_id or str(uuid.uuid4())}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/json",
            headers={"X-Correlation-ID": headers["X-Correlation-ID"]},
        )
    except httpx.RequestError as exc:
        logger.error(f"Failed to proxy request to order service: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Order service unavailable: {str(exc)}",
        )


@app.get("/api/v1/orders", tags=["orders"])
async def list_orders_proxy(
    skip: int = 0,
    limit: int = 50,
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    """Proxy list orders to Order Service."""
    url = f"{settings.order_service_url.rstrip('/')}/orders?skip={skip}&limit={limit}"
    headers = {"X-Correlation-ID": x_correlation_id or str(uuid.uuid4())}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/json",
            headers={"X-Correlation-ID": headers["X-Correlation-ID"]},
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Order service unavailable: {str(exc)}",
        )


@app.get("/api/v1/payments/{payment_id}", tags=["payments"])
async def get_payment_proxy(
    payment_id: str,
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    """Proxy payment lookup to Payment Service."""
    url = f"{settings.payment_service_url.rstrip('/')}/payments/{payment_id}"
    headers = {"X-Correlation-ID": x_correlation_id or str(uuid.uuid4())}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type="application/json",
            headers={"X-Correlation-ID": headers["X-Correlation-ID"]},
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Payment service unavailable: {str(exc)}",
        )

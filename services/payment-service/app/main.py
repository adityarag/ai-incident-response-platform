"""
Payment Service — Main FastAPI Application

Handles payment transactions, supports idempotency, records payments
into PostgreSQL, and exposes health and metrics.
"""

import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.schemas import PaymentProcessRequest, PaymentResponse

# ── Logging & Observability ────────────────────────────────

try:
    from observability.telemetry import setup_service_logger, attach_observability, setup_opentelemetry
    logger = setup_service_logger("payment-service")
except ImportError:
    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_obj = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": "payment-service",
                "message": record.getMessage(),
                "logger": record.name,
            }
            if hasattr(record, "correlation_id"):
                log_obj["correlation_id"] = record.correlation_id
            return json.dumps(log_obj)

    logger = logging.getLogger("payment-service")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    attach_observability = None
    setup_opentelemetry = None

# ── Database Session Setup ─────────────────────────────────

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def _check_db() -> dict:
    try:
        from fault_injection.manager import fault_manager
        if fault_manager.is_db_failure_simulated("payment-service"):
            return {"status": "disconnected", "error": "Simulated database connection failure / pool exhaustion"}
    except ImportError:
        pass

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return {"status": "disconnected", "error": str(exc)}


# ── Lifespan ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Payment Service starting up")
    db_health = _check_db()
    logger.info(f"Database check: {db_health['status']}")
    yield
    logger.info("Payment Service shutting down")


# ── FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title="AI Incident Response Platform — Payment Service",
    description="Processes and manages transaction records for orders.",
    version="0.1.0",
    lifespan=lifespan,
)

try:
    from fault_injection.middleware import attach_fault_injection
    attach_fault_injection(app, "payment-service")
except ImportError:
    pass

if attach_observability:
    attach_observability(app, "payment-service")
if setup_opentelemetry:
    setup_opentelemetry("payment-service", app)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response


# ── Health Endpoints ───────────────────────────────────────

@app.get("/health", tags=["health"])
def health():
    db = _check_db()
    overall = "healthy" if db["status"] == "connected" else "degraded"
    return {
        "status": overall,
        "service": "payment-service",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db,
        },
    }


@app.get("/ready", tags=["health"])
def readiness():
    db = _check_db()
    ready = db["status"] == "connected"
    return {
        "ready": ready,
        "service": "payment-service",
    }


# ── Payment Processing Endpoints ───────────────────────────

@app.post(
    "/payments/process",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["payments"],
)
def process_payment(
    payment_in: PaymentProcessRequest,
    db: Session = Depends(get_db),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    """
    Process a payment for an order.
    Supports idempotency via idempotency_key.
    """
    from database.models import Payment, PaymentStatus

    # Check idempotency
    if payment_in.idempotency_key:
        stmt = select(Payment).where(Payment.idempotency_key == payment_in.idempotency_key)
        existing = db.execute(stmt).scalar_one_or_none()
        if existing:
            logger.info(
                f"Idempotent payment match found: {existing.payment_id}",
                extra={"correlation_id": x_correlation_id},
            )
            return existing

    # Simulating standard payment flow
    # In real scenarios or fault injection, this could be triggered to fail
    is_success = True
    failure_reason = None

    payment_record = Payment(
        payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
        order_id=payment_in.order_id,
        customer_id=payment_in.customer_id,
        amount=payment_in.amount,
        currency=payment_in.currency,
        status=PaymentStatus.SUCCESS if is_success else PaymentStatus.FAILED,
        failure_reason=failure_reason,
        idempotency_key=payment_in.idempotency_key,
    )

    db.add(payment_record)
    db.commit()
    db.refresh(payment_record)

    logger.info(
        f"Processed payment {payment_record.payment_id} for order {payment_record.order_id}: {payment_record.status.value}",
        extra={"correlation_id": x_correlation_id},
    )

    return payment_record


@app.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["payments"],
)
def get_payment(payment_id: str, db: Session = Depends(get_db)):
    from database.models import Payment

    stmt = select(Payment).where(Payment.payment_id == payment_id)
    payment = db.execute(stmt).scalar_one_or_none()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found",
        )
    return payment

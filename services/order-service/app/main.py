"""
Order Service — Main FastAPI Application

Manages customer orders, orchestrates payments via the Payment Service,
and writes to PostgreSQL.
"""

import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import Depends, FastAPI, HTTPException, Header, Request, status
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.schemas import OrderCreateRequest, OrderResponse

# ── Logging & Observability ────────────────────────────────

try:
    from observability.telemetry import setup_service_logger, attach_observability, setup_opentelemetry
    logger = setup_service_logger("order-service")
except ImportError:
    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_obj = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "service": "order-service",
                "message": record.getMessage(),
                "logger": record.name,
            }
            if hasattr(record, "correlation_id"):
                log_obj["correlation_id"] = record.correlation_id
            return json.dumps(log_obj)

    logger = logging.getLogger("order-service")
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
        if fault_manager.is_db_failure_simulated("order-service"):
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
    logger.info("Order Service starting up")
    db_health = _check_db()
    logger.info(f"Database check: {db_health['status']}")
    yield
    logger.info("Order Service shutting down")


# ── FastAPI App ────────────────────────────────────────────

app = FastAPI(
    title="AI Incident Response Platform — Order Service",
    description="Manages order lifecycles and coordinates with Payment Service.",
    version="0.1.0",
    lifespan=lifespan,
)

try:
    from fault_injection.middleware import attach_fault_injection
    attach_fault_injection(app, "order-service")
except ImportError:
    pass

if attach_observability:
    attach_observability(app, "order-service")
if setup_opentelemetry:
    setup_opentelemetry("order-service", app)


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
        "service": "order-service",
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
        "service": "order-service",
    }


# ── Order Management Endpoints ─────────────────────────────

@app.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["orders"],
)
async def create_order(
    order_in: OrderCreateRequest,
    db: Session = Depends(get_db),
    x_correlation_id: str | None = Header(None, alias="X-Correlation-ID"),
):
    from database.models import Order, OrderStatus

    settings = get_settings()
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    # Create initial pending order
    order_record = Order(
        order_id=order_id,
        customer_id=order_in.customer_id,
        item=order_in.item,
        quantity=order_in.quantity,
        amount=order_in.amount,
        currency=order_in.currency,
        status=OrderStatus.PENDING,
    )
    db.add(order_record)
    db.commit()
    db.refresh(order_record)

    logger.info(
        f"Created order {order_id} with status PENDING",
        extra={"correlation_id": x_correlation_id},
    )

    # Call downstream Payment Service
    payment_url = f"{settings.payment_service_url.rstrip('/')}/payments/process"
    payment_payload = {
        "order_id": order_id,
        "customer_id": order_in.customer_id,
        "amount": order_in.amount,
        "currency": order_in.currency,
        "idempotency_key": f"idemp-{order_id}",
    }

    headers = {}
    if x_correlation_id:
        headers["X-Correlation-ID"] = x_correlation_id

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(payment_url, json=payment_payload, headers=headers)

        if resp.status_code == 201:
            pay_data = resp.json()
            if pay_data.get("status") == "SUCCESS":
                order_record.status = OrderStatus.COMPLETED
                order_record.payment_id = pay_data.get("payment_id")
            else:
                order_record.status = OrderStatus.FAILED
                order_record.failure_reason = pay_data.get("failure_reason", "Payment failed")
        else:
            order_record.status = OrderStatus.FAILED
            order_record.failure_reason = f"Payment service returned HTTP {resp.status_code}"

    except httpx.RequestError as exc:
        logger.error(
            f"Failed to communicate with payment service: {exc}",
            extra={"correlation_id": x_correlation_id},
        )
        order_record.status = OrderStatus.FAILED
        order_record.failure_reason = f"Payment service unreachable: {str(exc)}"

    db.commit()
    db.refresh(order_record)

    logger.info(
        f"Order {order_id} final status: {order_record.status.value}",
        extra={"correlation_id": x_correlation_id},
    )

    return order_record


@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    tags=["orders"],
)
def get_order(order_id: str, db: Session = Depends(get_db)):
    from database.models import Order

    stmt = select(Order).where(Order.order_id == order_id)
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
    return order


@app.get(
    "/orders",
    response_model=List[OrderResponse],
    tags=["orders"],
)
def list_orders(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    from database.models import Order

    stmt = select(Order).offset(skip).limit(limit)
    orders = db.execute(stmt).scalars().all()
    return list(orders)

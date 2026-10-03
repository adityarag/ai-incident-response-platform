"""
Shared database models for the AI Incident Response Platform.

All SQLAlchemy models are defined here. Services import from this module.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


# ── Enums ──────────────────────────────────────────────────

class ServiceStatus(str, PyEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class IncidentSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, PyEnum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class IncidentType(str, PyEnum):
    HIGH_ERROR_RATE = "HIGH_ERROR_RATE"
    HIGH_LATENCY = "HIGH_LATENCY"
    SERVICE_DOWN = "SERVICE_DOWN"
    POD_CRASH_LOOP = "POD_CRASH_LOOP"
    DATABASE_FAILURE = "DATABASE_FAILURE"
    API_SCHEMA_CHANGE = "API_SCHEMA_CHANGE"
    DEPLOYMENT_FAILURE = "DEPLOYMENT_FAILURE"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"


class OrderStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, PyEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ── Models ─────────────────────────────────────────────────

class Service(Base):
    """Registered service in the platform."""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    health_endpoint = Column(String(512), nullable=True)
    status = Column(
        Enum(ServiceStatus),
        nullable=False,
        default=ServiceStatus.UNKNOWN,
    )
    version = Column(String(64), nullable=True)
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Service(name={self.name!r}, status={self.status!r})>"


class Incident(Base):
    """An incident detected by the platform."""

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        String(64), unique=True, nullable=False, index=True
    )
    service = Column(String(255), nullable=False, index=True)
    severity = Column(Enum(IncidentSeverity), nullable=False)
    type = Column(Enum(IncidentType), nullable=False)
    status = Column(
        Enum(IncidentStatus),
        nullable=False,
        default=IncidentStatus.DETECTED,
    )
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Incident(id={self.incident_id!r}, "
            f"service={self.service!r}, "
            f"status={self.status!r})>"
        )


class AuditLog(Base):
    """Immutable audit trail for all platform actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(255), nullable=False, index=True)
    actor = Column(String(255), nullable=False)  # "system", "ai-agent", "user:xyz"
    target = Column(String(255), nullable=True)
    detail = Column(Text, nullable=True)
    incident_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action={self.action!r}, "
            f"actor={self.actor!r})>"
        )


class Order(Base):
    """Customer order record."""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(64), unique=True, nullable=False, index=True)
    customer_id = Column(String(64), nullable=False, index=True)
    item = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
    )
    payment_id = Column(String(64), nullable=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.order_id!r}, status={self.status!r}, amount={self.amount!r})>"


class Payment(Base):
    """Processed transaction record."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String(64), unique=True, nullable=False, index=True)
    order_id = Column(String(64), nullable=False, index=True)
    customer_id = Column(String(64), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    failure_reason = Column(Text, nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.payment_id!r}, order_id={self.order_id!r}, status={self.status!r})>"

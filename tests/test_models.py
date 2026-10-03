"""
Tests for the database models module.

These tests verify model definitions, enum values, and schema
correctness without requiring a running database.
"""

import pytest

from database.models import (
    AuditLog,
    Base,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Service,
    ServiceStatus,
)


class TestServiceModel:
    """Tests for the Service model."""

    def test_service_tablename(self):
        assert Service.__tablename__ == "services"

    def test_service_has_required_columns(self):
        columns = {c.name for c in Service.__table__.columns}
        expected = {
            "id", "name", "display_name", "description",
            "health_endpoint", "status", "version",
            "last_health_check", "created_at", "updated_at",
        }
        assert expected.issubset(columns)

    def test_service_repr(self):
        svc = Service()
        svc.name = "test-svc"
        svc.status = ServiceStatus.HEALTHY
        assert "test-svc" in repr(svc)


class TestIncidentModel:
    """Tests for the Incident model."""

    def test_incident_tablename(self):
        assert Incident.__tablename__ == "incidents"

    def test_incident_has_required_columns(self):
        columns = {c.name for c in Incident.__table__.columns}
        expected = {
            "id", "incident_id", "service", "severity", "type",
            "status", "title", "description", "root_cause",
            "confidence", "detected_at", "resolved_at",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns)


class TestAuditLogModel:
    """Tests for the AuditLog model."""

    def test_audit_log_tablename(self):
        assert AuditLog.__tablename__ == "audit_logs"

    def test_audit_log_has_required_columns(self):
        columns = {c.name for c in AuditLog.__table__.columns}
        expected = {
            "id", "action", "actor", "target",
            "detail", "incident_id", "timestamp",
        }
        assert expected.issubset(columns)


class TestOrderModel:
    """Tests for the Order model."""

    def test_order_tablename(self):
        assert Order.__tablename__ == "orders"

    def test_order_has_required_columns(self):
        columns = {c.name for c in Order.__table__.columns}
        expected = {
            "id", "order_id", "customer_id", "item",
            "quantity", "amount", "currency", "status",
            "payment_id", "failure_reason",
            "created_at", "updated_at",
        }
        assert expected.issubset(columns)


class TestPaymentModel:
    """Tests for the Payment model."""

    def test_payment_tablename(self):
        assert Payment.__tablename__ == "payments"

    def test_payment_has_required_columns(self):
        columns = {c.name for c in Payment.__table__.columns}
        expected = {
            "id", "payment_id", "order_id", "customer_id",
            "amount", "currency", "status", "failure_reason",
            "idempotency_key", "created_at", "updated_at",
        }
        assert expected.issubset(columns)


class TestOrderStatusEnum:
    """Tests for OrderStatus enum."""

    def test_all_order_statuses_exist(self):
        expected = {"PENDING", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"}
        actual = {s.value for s in OrderStatus}
        assert actual == expected


class TestPaymentStatusEnum:
    """Tests for PaymentStatus enum."""

    def test_all_payment_statuses_exist(self):
        expected = {"PENDING", "SUCCESS", "FAILED", "REFUNDED"}
        actual = {s.value for s in PaymentStatus}
        assert actual == expected


class TestServiceStatusEnum:
    """Tests for ServiceStatus enum values."""

    def test_all_statuses_exist(self):
        expected = {"HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"}
        actual = {s.value for s in ServiceStatus}
        assert actual == expected


class TestIncidentStatusEnum:
    """Tests for the incident state machine enum."""

    def test_all_states_exist(self):
        """Verify all states from the spec's incident state machine."""
        expected = {
            "DETECTED", "INVESTIGATING", "ROOT_CAUSE_IDENTIFIED",
            "REMEDIATION_PROPOSED", "AWAITING_APPROVAL",
            "REMEDIATING", "VERIFYING", "RESOLVED",
            "FAILED", "ESCALATED",
        }
        actual = {s.value for s in IncidentStatus}
        assert actual == expected

    def test_state_count(self):
        """The state machine should have exactly 10 states."""
        assert len(IncidentStatus) == 10


class TestIncidentSeverityEnum:
    """Tests for severity levels."""

    def test_all_severities_exist(self):
        expected = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        actual = {s.value for s in IncidentSeverity}
        assert actual == expected


class TestIncidentTypeEnum:
    """Tests for incident types."""

    def test_all_types_exist(self):
        expected = {
            "HIGH_ERROR_RATE", "HIGH_LATENCY", "SERVICE_DOWN",
            "POD_CRASH_LOOP", "DATABASE_FAILURE", "API_SCHEMA_CHANGE",
            "DEPLOYMENT_FAILURE", "RESOURCE_EXHAUSTION",
        }
        actual = {t.value for t in IncidentType}
        assert actual == expected


class TestDeclarativeBase:
    """Tests for SQLAlchemy base configuration."""

    def test_base_has_metadata(self):
        assert Base.metadata is not None

    def test_tables_registered(self):
        """All models should be registered in Base.metadata."""
        table_names = set(Base.metadata.tables.keys())
        assert "services" in table_names
        assert "incidents" in table_names
        assert "audit_logs" in table_names
        assert "orders" in table_names
        assert "payments" in table_names

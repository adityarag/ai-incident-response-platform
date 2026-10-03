"""
Comprehensive Tests for Controlled Fault Injection Engine.

Verifies:
1. Fault disabled -> normal behavior
2. Fault enabled (latency) -> delay observed and recorded in metrics
3. Fault enabled (error spike) -> 5xx status returned and recorded in metrics
4. Fault enabled (db failure) -> service health reflects degraded/disconnected
5. Fault cleared -> immediate recovery
6. Evidence model generation
"""

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fault_injection.manager import fault_manager
from fault_injection.middleware import attach_fault_injection
from fault_injection.models import (
    FaultClearRequest,
    FaultInjectRequest,
    FaultType,
)
from fault_injection.evidence import capture_incident_evidence
from observability.telemetry import attach_observability


@pytest.fixture(autouse=True)
def clean_faults():
    """Ensure clear state before and after each test."""
    fault_manager.clear_faults()
    yield
    fault_manager.clear_faults()


@pytest.fixture
def target_app():
    app = FastAPI()
    attach_fault_injection(app, "test-fault-service")
    attach_observability(app, "test-fault-service")

    @app.get("/items/standard")
    def standard_route():
        return {"status": "ok", "data": "item"}

    @app.get("/health")
    def health():
        if fault_manager.is_db_failure_simulated("test-fault-service"):
            return {"status": "degraded", "checks": {"database": "disconnected"}}
        return {"status": "healthy", "checks": {"database": "connected"}}

    return app


@pytest.fixture
def client(target_app):
    return TestClient(target_app)


class TestFaultInjectionEngine:
    def test_default_behavior_without_faults(self, client):
        resp = client.get("/items/standard")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "data": "item"}

    def test_latency_fault_injection_and_clearing(self, client):
        # 1. Inject 0.25s latency
        inject_req = FaultInjectRequest(
            service="test-fault-service",
            fault_type=FaultType.LATENCY,
            endpoint="/items/standard",
            latency_seconds=0.25,
            duration_seconds=30,
        )
        inject_resp = client.post("/faults/inject", json=inject_req.model_dump())
        assert inject_resp.status_code == 200
        assert inject_resp.json()["fault_type"] == "latency"

        # 2. Measure delayed response
        start_t = time.time()
        resp = client.get("/items/standard")
        duration = time.time() - start_t
        assert resp.status_code == 200
        assert duration >= 0.20  # Delay observed

        # 3. Clear fault
        clear_resp = client.post("/faults/clear", json={"service": "test-fault-service"})
        assert clear_resp.status_code == 200
        assert clear_resp.json()["cleared_count"] >= 1

        # 4. Measure recovered fast response
        start_fast = time.time()
        fast_resp = client.get("/items/standard")
        duration_fast = time.time() - start_fast
        assert fast_resp.status_code == 200
        assert duration_fast < 0.15

    def test_error_spike_fault_injection_and_metrics(self, client):
        # 1. Inject 100% 503 error spike
        inject_req = FaultInjectRequest(
            service="test-fault-service",
            fault_type=FaultType.ERROR_SPIKE,
            endpoint="/items/standard",
            error_rate=1.0,
            status_code=503,
            error_message="High downstream traffic spike",
        )
        client.post("/faults/inject", json=inject_req.model_dump())

        # 2. Trigger request -> should fail with 503
        err_resp = client.get("/items/standard")
        assert err_resp.status_code == 503
        data = err_resp.json()
        assert data["error"] == "FaultInjectionSimulatedError"
        assert data["detail"] == "High downstream traffic spike"

        # 3. Metrics should record the 503 error
        metrics_resp = client.get("/metrics")
        assert 'status="503"' in metrics_resp.text

        # 4. Clear and verify recovery
        client.post("/faults/clear", json={"service": "test-fault-service"})
        ok_resp = client.get("/items/standard")
        assert ok_resp.status_code == 200

    def test_database_failure_simulation(self, client):
        # 1. Initially healthy
        h1 = client.get("/health")
        assert h1.json()["status"] == "healthy"

        # 2. Inject DB failure
        inject_req = FaultInjectRequest(
            service="test-fault-service",
            fault_type=FaultType.DATABASE_FAILURE,
            duration_seconds=60,
        )
        client.post("/faults/inject", json=inject_req.model_dump())

        # 3. Health check should reflect degraded state
        h2 = client.get("/health")
        assert h2.json()["status"] == "degraded"
        assert h2.json()["checks"]["database"] == "disconnected"

        # 4. Clear DB fault and verify health restoration
        client.post("/faults/clear", json={"service": "test-fault-service"})
        h3 = client.get("/health")
        assert h3.json()["status"] == "healthy"

    def test_incident_evidence_generation(self):
        evidence = capture_incident_evidence(
            affected_service="payment-service",
            fault_type="database_failure",
            severity="HIGH",
            affected_endpoint="/payments/process",
            correlation_id="test-corr-abc",
            status_code=500,
            latency_observed_seconds=3.42,
            relevant_logs=[{"level": "ERROR", "msg": "Connection pool timeout"}],
        )

        assert evidence.incident_id.startswith("INC-")
        assert evidence.affected_service == "payment-service"
        assert evidence.fault_type == "database_failure"
        assert evidence.severity == "HIGH"
        assert evidence.correlation_id == "test-corr-abc"
        assert evidence.latency_observed_seconds == 3.42
        assert len(evidence.relevant_logs) == 1
        assert evidence.recovery_status == "DETECTED"

# Controlled Fault Injection Framework

## Overview

The fault injection framework allows developers and operators to introduce controlled, safe, non-destructive, and reversible failures into the local microservices architecture. It simulates real-world outages to validate the observability stack (Prometheus, Loki, Grafana, OpenTelemetry) and prepare realistic training/evaluation incident data for the upcoming AI investigation agent (Phase 5).

---

## 1. Safety & Guardrails

- **Local Scope**: Injections only affect the local runtime / container environment.
- **Zero Data Loss**: Database failures simulate connection refusal and pool exhaustion. No records, schemas, or tables are deleted or corrupted.
- **Auto-Expiration (TTL)**: All injected faults support an optional `duration_seconds` timer (default: 60s) after which they automatically expire and self-clear.
- **Immediate Reversal**: Any fault can be cleared immediately using the `/faults/clear` endpoint or CLI.
- **Protected Endpoints**: Health probes (`/health`, `/ready`), metrics (`/metrics`), and management routes (`/faults/*`) are excluded from injection to prevent blind system lockups.

---

## 2. Supported Fault Scenarios

| Fault Scenario | Type | Description | Symptoms / Expected Metrics |
|---|---|---|---|
| **Artificial Latency** | `latency` | Injects sleep delay into request processing | P95 latency histogram spike on `http_request_duration_seconds` |
| **Error Spike** | `error_spike` | Injects HTTP 5xx responses at configurable rate | `http_requests_total{status="500"}` spike, error logs in Loki |
| **Database Failure** | `database_failure` | Simulates DB connection pool drop | `/health` reports `status: degraded`, `checks.database: disconnected` |
| **Dependency Timeout** | `dependency_timeout` | Simulates downstream service timeout | HTTP 504 Gateway Timeout, inter-service retry failure |
| **Service Outage** | `service_crash` | Controlled process crash or container pause | Health check failures, target service drops from scrape targets |

---

## 3. CLI Usage

The framework includes a standalone CLI tool [`fault_injection/cli.py`](file:///c:/Users/adity/Desktop/ai-incident-response-platform/fault_injection/cli.py):

### A. Inject Artificial Latency
```bash
# Inject 3 seconds latency into payment-service for 60 seconds
python fault_injection/cli.py latency --service payment-service --seconds 3.0 --duration 60

# Inject latency only for order creation on api-gateway
python fault_injection/cli.py latency --service api-gateway --endpoint /api/v1/orders --seconds 2.5
```

### B. Inject 5xx Error Spike
```bash
# Force 80% error rate returning HTTP 500 on order-service
python fault_injection/cli.py error-spike --service order-service --rate 0.8 --status 500 --duration 45

# Force 100% 503 Service Unavailable on payment-service
python fault_injection/cli.py error-spike --service payment-service --rate 1.0 --status 503
```

### C. Simulate Database Failure
```bash
# Simulate database unavailability on payment-service
python fault_injection/cli.py db-failure --service payment-service --duration 60
```

### D. List Active Faults
```bash
python fault_injection/cli.py list
```

### E. Clear / Recover from Faults
```bash
# Clear all faults across all services
python fault_injection/cli.py clear

# Clear faults on a specific service
python fault_injection/cli.py clear --service payment-service
```

---

## 4. Programmatic HTTP API

Each microservice exposes the following fault management endpoints:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/faults/inject` | Injects fault scenario |
| `POST` | `/faults/clear` | Clears active faults |
| `GET` | `/faults/active` | Queries currently active faults |

### Example Injection Request Body
```json
{
  "service": "payment-service",
  "fault_type": "error_spike",
  "endpoint": "/payments/process",
  "error_rate": 1.0,
  "status_code": 500,
  "error_message": "Payment gateway connection timeout",
  "duration_seconds": 60
}
```

---

## 5. Normalized Incident Evidence Schema

When a fault triggers, the platform captures a normalized `IncidentEvidence` object:

```json
{
  "incident_id": "INC-7D9A41C2",
  "timestamp": "2026-10-03T15:10:00.000Z",
  "affected_service": "payment-service",
  "affected_endpoint": "/payments/process",
  "fault_type": "error_spike",
  "severity": "HIGH",
  "correlation_id": "97e68fa2-6825-45d6-848d-6a3f47e09210",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "status_code": 500,
  "latency_observed_seconds": 3.12,
  "metrics_snapshot": {
    "error_rate": 1.0,
    "http_5xx_count": 42
  },
  "relevant_logs": [
    {
      "level": "ERROR",
      "message": "Injecting simulated error (500) on /payments/process"
    }
  ],
  "recovery_status": "DETECTED"
}
```
